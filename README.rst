A tool that takes care of merging approved merge requests, on GitLab
(gitlab.com or self-managed). It sets them as "auto-merge", rebases
the corresponding branches, and restarts CI jobs that randomly
fail. Without you having to supervise anything.


Context
=======

Your merge request has been approved, you set "auto-merge" on it. You
wait... and one of the CI jobs fails for some random reason. Too bad.
You restart the job. You wait. The job fails. Again. You restart the
job. It finally succeds...  but another merge request has been merged
in the meantime, and your branch must thus be rebased. You do that and
set "auto-merge". You wait for the pipeline... and, yes, you guessed:
one of the CI job failed again. And that's only one of the several
merge requests that are ready to be merged.

You pause. You take a breath. Then you run:

.. code-block::

    $ gitlab_automerger --author jdoe

… and get back to what it is you were working on, while the tool, with
its (almost) infinite patience, handles your merge requests.


Installation
============

This tool requires Python.

Quick (and not too dirty):

.. code-block:: bash

    $ export VENV=~/.venv/gitlab_automerger
    $ mkdir --parents $VENV
    $ python3 -m venv $VENV
    $ $VENV/bin/pip install --upgrade pip python-gitlab
    $ git clone https://github.com/dbaty/gitlab_automerger $VENV/src/gitlab_automerger
    $ alias gitlab_automerger="$VENV/bin/python $VENV/src/gitlab_automerger/src/gitlab_automerger.py"

FIXME: publish package on PyPI, or suggest `uv` or something else...


Configuration
=============

1. Set ``$GITLAB_API_URL`` environment variable. It's the root of your
   GitLab private instance, or "https://gitlab.com".

2. Set ``$GITLAB_API_TOKEN`` environment variable with a valid GitLab
   token with the ``api`` scope.

You are ready.


Usage
=====

Note: ``gitlab_automerger`` merges only **approved** merge requests.

To merge all approved requests of a specific users:

.. code-block::

    $ gitlab_automerger --repository org/poject --author jsmith

To merge 2 specific merge requests:

.. code-block::

    $ gitlab_automerger --repository org/poject --mr 123 --mr 245

If one of the specified merge request is not approved, an error
message is displayed and the merge request is not processed. This is a
safety belt, in case you provide the wrong number and your GitLab
projet settings would not block the merge.

The other main feature:

.. code-block::

    $ gitlab_automerger --help
    usage: gitlab_automerger.py [-h] --repository REPOSITORY [--author USERNAME] [--mr NUMBER]

    Automatically rebase and set to auto-merge a list of approved merge requests

    options:
      -h, --help            show this help message and exit
      --repository REPOSITORY
                            Name of the GitLab project, as "org_name/project_name".
      --author USERNAME     Filter on this author's approved merge requests. Use this option or `--mr`.
      --mr NUMBER           Process this (or these) specific merge request(s). Option can be used multiple times. Use this option or `--author`.

``--author`` and ``--mr`` options are exclusive. But one of them is required.


Merge conditions
================

``gitlab_automerger`` merely sets "auto-merge", rebases (through the
GitLab API, not through `git`), and retries failing CI jobs. Thus, it
will fail to merge (and display an error message):

- if a CI job fails more than 3 times;
- or if it cannot be automatically rebased;
- or for any other reason that would block the merge (such as the "All
  threads must be resolved" setting).


Output example
==============

.. code-block::

    $ gitlab_automerger --repository client/secret-project --mr 345 --mr 382
    Processing MR #345 ([ABC-123] Implement frobulation endpoint)...
    └ rebasing...
    └ polling status of pipeline 692565...
    └ rebasing...
    └ polling status of pipeline 692570...
    └ rebasing...
    └ polling status of pipeline 692577...
    └ merged
    Processing MR #382 ([ABC-87] Allow user to cropinate frabulines)...
    └ rebasing...
    └ polling status of pipeline 692577...
    └ merged
    2 merge request(s) have been merged:
    - MR #345: [ABC-123] Implement frobulation endpoint
    - MR #382: [ABC-87] Allow user to cropinate frabulines

… with shiny colors, but not too much: it's a terminal, not a
Christmas tree.


Limitations
===========

GitLab API errors, network issues and the like are not handled.


FAQ
===

These questions were not frequently asked. I just made them up.

Shouldn't I rather fix randomly failing CI jobs?
------------------------------------------------

Please don't ask that. How could I enjoy writing a questionable tool
and this silly README if I solved the underlying issues?

Of course I agree. If your CI jobs fail because of flaky tests, fix
the tests. If they fail because of network errors or obscur GitLab
runner issues, tro to fix that, too. If you can't, use this tool.

Why not use merge trains?
-------------------------

GitLab's `merge trains`_ may be a solution to the problem this tool
solves. This feature is not available with GitLab Free, unfortunately.

Can I trust you with my GitLab API access token?
------------------------------------------------

There is no good answer to that, is there? I suggest that you read the
very few amount of code of this tool. Then you'll have to trust the
`python-gitlab`_ Python package that this tool heavily relies on. It's
slightly bigger, but it seems to be well-maintained and safe. Ok, now
my lawyer is giving me a stern look, so don't quote me on that.


.. _merge trains: https://docs.gitlab.com/ci/pipelines/merge_trains/
.. _python-gitlab: https://python-gitlab.readthedocs.io/
