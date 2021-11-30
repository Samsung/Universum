Integrate collapsible log into Jenkins
======================================

The `--html-log <args.html#Output>`__ option enables generating an HTML page with collapsible blocks,
very convenient when navigating a long build log of a `Universum` run with many steps.

While TeamCity has its own mechanisms increasing readability, and Universum ran locally by default just stores
step execution logs to files to be accessed separately, Jenkins just provides the full build log, formatted as
a very long text with no real anchors. Generating a user-friendly log and integrating it into a `Universum` job
simplifies interaction with `Univesrum` in CI process.

One of possible ways to integrate an existing log to Jenkins job is `htmlpublisher
<https://plugins.jenkins.io/htmlpublisher/>`__ plugin. After installing it to your server, apply
the following changes:

1. Add ``-hl``/``--html-log``/``-hl <name>`` option to the `Universum` command line
2. Pass default or customized log name to plugin configuration as described in manual
   (https://plugins.jenkins.io/htmlpublisher/) via `Post-build Actions` or pipeline
3. Let Jenkins render the interactive content of log (see https://www.jenkins.io/doc/book/security/user-content/
   details)

The easiest way to execute the last step proposed above is to `configure Jenkins to publish artifacts on a different
domain <https://www.jenkins.io/doc/book/security/user-content/#resource-root-url>`__ by changing ``Resource Root URL``
in `Manage Jenkins » Configure System » Serve resource files from another domain` from something like
``my.jenkins.io`` to ``res.my.jenkins.io``.


Using subdomain with Nginx reverse-proxy
----------------------------------------

Please pay attention, that server interaction with resource subdomain is not done via ``localhost`` network interface,
but involves full scale redirecting to an external resource. This means that:

1. Both ``my.jenkins.io`` and ``res.my.jenkins.io`` domain names should be resolved correctly
2. All headers should be passed correctly

In case your Jenkins server is launched behind the Nginx reverse-proxy (which is a quite common configuration),
default behaviour is to replace ``Host`` headers on redirection. To pass them correctly, adjust the configuration
accordingly (see https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/#passing-request-headers for
more details).

.. note::

    Also, setting the ``server_name`` to both main domain and a subdomain might be needed
