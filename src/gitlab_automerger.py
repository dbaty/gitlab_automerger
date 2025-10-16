import argparse
import os
import sys
import time

import gitlab
import gitlab.exceptions


PIPELINE_POLL_INTERVAL = 30  # seconds
PIPELINE_POLL_MAX_DURATION = 15 * 60  # 15 minutes
MAXIMUM_JOB_RETRIES = 3


def main():
    gl = get_client()
    args = parse_args()
    project = gl.projects.get(args.repository)

    if args.author:
        mrs = project.mergerequests.list(
            state='opened',
            author_username=args.author,
            approved_by_ids='Any',
            order_by='created_at',
            sort='asc',
        )
    elif args.merge_requests:
        mrs = [project.mergerequests.get(iid) for iid in args.merge_requests]
        mrs = list(only_approved(mrs))
    else:
        sys.exit("Wrong usage: either `--author` or `--mr` is required, not both.")

    if not mrs:
        print(success("No merge request to process."))
        sys.exit(0)

    print(f"Found {len(mrs)} merge request(s) to process.")

    merged = []
    not_merged = []
    for mr in mrs:
        if merge(project, mr):
            merged.append(mr)
        else:
            not_merged.append(mr)
    if merged:
        print(success(f"{len(merged)} merge request(s) have been merged:"))
        for mr in merged:
            print(success(f"- MR #{mr.iid}: {mr.title}"))
    if not_merged:
        print(error(f"{len(not_merged)} merge request(s) could not be merged:"))
        for mr in not_merged:
            print(error(f"- MR #{mr.iid}: {mr.title}"))


def only_approved(mrs):
    for mr in mrs:
        # Do not use the `approved` boolean attribute. It means: "did
        # the MR receive all required approvals?" It is always true if
        # no approval is required (which is the only behaviour in
        # GitLab Free, for example).
        if not mr.approvals.get().approved_by:
            print(error(f"MR #{mr.iid} is not approved and will not be processed."))
            continue
        yield mr


def get_client():
    try:
        url = os.environ["GITLAB_API_URL"]
        token = os.environ["GITLAB_API_TOKEN"]
    except KeyError as err:
        sys.exit(f"Missing environment variable: ${err.args[0]}")
    return gitlab.Gitlab(url, token)


def parse_args():
    parser = argparse.ArgumentParser(description="Automatically rebase and set to auto-merge a list of approved merge requests")
    parser.add_argument(
        "--repository",
        required=True,
        metavar="REPOSITORY",
        help='Name of the GitLab project, as "org_name/project_name".',
    )
    parser.add_argument(
        "--author",
        metavar="USERNAME",
        help="Filter on this author's approved merge requests. Use this option or `--mr`.",
    )
    parser.add_argument(
        '--mr',
        action="append",
        dest="merge_requests",
        metavar="NUMBER",
        help="Process this (or these) specific merge request(s). Option can be used multiple times. Use this option or `--author`.",
    )

    return parser.parse_args()


def wait_for_pipeline(project, pipeline_id):
    polling_start = time.perf_counter()
    print(neutral(f"└ polling status of pipeline {pipeline_id}..."))
    while time.perf_counter() - polling_start < PIPELINE_POLL_MAX_DURATION:
        pipeline = project.pipelines.get(pipeline_id)
        if pipeline.status in ('success', 'failed', 'canceled'):
            return pipeline
        time.sleep(PIPELINE_POLL_INTERVAL)
    return None


def merge(project, mr):
    print(f"Processing MR #{mr.iid} ({mr.title})...")
    # `mr` is a lightweight object that does not have all properties.
    # Fetch it again to get all properties.
    mr = project.mergerequests.get(mr.iid)
    job_restart_attempts = 0
    while 1:
        mr = project.mergerequests.get(mr.iid)
        if mr.state == 'merged':
            print(success("└ merged"))
            return True
        if mr.detailed_merge_status == 'need_rebase':
            print(neutral("└ rebasing..."))
            mr.rebase()
            # Leave GitLab some time to perform the rebase and start a
            # new pipeline.
            time.sleep(10)
            # Fetch MR again so that we get the new pipeline that was
            # created by the rebase.
            mr = project.mergerequests.get(mr.iid)
            job_restart_attempts = 0
        try:
            mr.merge(merge_when_pipeline_succeeds=True)
        except gitlab.GitlabMRClosedError:
            if mr.detailed_merge_status != 'checking':
                # FIXME: debugging statement, in case we get an unexpected status.
                print(neutral(f"└ cannot be merged yet, because {mr.detailed_merge_status}"))
        pipeline_id = mr.head_pipeline["id"]
        pipeline = wait_for_pipeline(project, pipeline_id)
        if not pipeline:
            print(error(f"└ timed out waiting for pipeline {pipeline_id}"))
            return False
        if pipeline.status == 'success':
            mr = project.mergerequests.get(mr.iid)
            if mr.state == 'merged':
                print(success("└ merged"))
                return True
            if mr.detailed_merge_status == 'mergeable':
                # MR is ready to be merged, but... it has not been
                # merged yet? We can just wait a bit...
                continue
            if mr.detailed_merge_status != 'need_rebase':
                print(error(f"└ cannot be merged, because {mr.detailed_merge_status}"))
                return False
        else:
            if job_restart_attempts > MAXIMUM_JOB_RETRIES:
                print(error("└ aborted merge, too much job retries"))
                return False
            print(neutral("└ restarting failed jobs..."))
            pipeline.retry()


def neutral(text):
    return text


def success(text):
    return f"\033[92m{text}\033[0m"  # green


def error(text):
    return f"\033[91m{text}\033[0m"  # red


if __name__ == '__main__':
    main()
