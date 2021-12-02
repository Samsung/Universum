Integration with Jenkins
========================

In `Jenkins` `Universum` is usually launched via single ``{python} -m universum`` command as one long step in a
single build stage. Because of that, the whole `Universum` log is printed as a plain text without navigation anchors.

.. admonition:: Compare with these:

    * When ran locally, all Universum build step logs are stored to separate files instead of printing their
      output to console
    * When launched on TeamCity, `Unviersum` uses `service messages
      <https://www.jetbrains.com/help/teamcity/service-messages.html>`__ to increase log readability

To simplify integration and debug, we provide a user-friendly interactive log with collapsible blocks and
other features. This log is generated when `--html-log <args.html#Output>`__ option is passed to command line.
It can be accessed from project `artifacts <args.html#Artifact\ collection>`__.

.. note::

    By default, Jenkins `does not render interactive content <https://www.jenkins.io/doc/book/security/user-content/>`__.
    This means that without changing server settings, interactive features of the generated log will be
    inaccessible when opened directly from Jenkins artifacts.


Jenkins Content-Security-Policy
-------------------------------

A recommended way to allow Jenkins server to render interactive user content is to `configure Jenkins to publish
artifacts on a different domain <https://www.jenkins.io/doc/book/security/user-content/#resource-root-url>`__
by changing ``Resource Root URL`` in `Manage Jenkins » Configure System » Serve resource files from another domain`
from something like ``my.jenkins.io`` to ``res.my.jenkins.io``.

Note that Jenkins interaction with resource domain, located on the same host is not done via ``localhost``
network interface. Jenkins treats ``another domain`` as an external URL when redirecting. This means that:

1. Both ``my.jenkins.io`` and ``res.my.jenkins.io`` domain names must be resolved correctly
2. All headers must be passed correctly

.. note::

    If main server domain name is not resolved using DNS, ``/etc/hosts`` or any other means, the web-interface
    will only be accessible via IP, and not the name. As resource domain might be located at the same IP,
    the resolving of both names is crucial

Here are the symptoms of domain names not resolving correctly:

1. Jenkins warnings when trying to save the updated settings
2. Client inability to access said pages (timeout error)

A reason for headers not passed correctly can be Nginx configuration. Without specification Nginx replaces
``Host`` headers on redirection, that will lead to ``404 NOT FOUND`` errors when trying to access artifacts
from Jenkins. To pass them correctly, adjust the configuration accordingly (see
https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/#passing-request-headers for more details).

.. note::

    Also you might need to set ``server_name`` to ``my.jenkins.io res.my.jenkins.io`` if they are located
    on the same host


Further integration
-------------------

To integrate the generated log into `Jenkins` job, we suggest `htmlpublisher <https://plugins.jenkins.io/htmlpublisher/>`__
plugin. After installing it to your server, apply the following changes:

1. Add ``-hl``/``--html-log``/``-hl <name>`` option to the `Universum` command line
2. Pass the log name to plugin configuration as described in manual (https://plugins.jenkins.io/htmlpublisher/)
   via `Post-build Actions` or pipeline
3. Let Jenkins render the interactive content of log (the section above)
