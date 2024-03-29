Integration with Jenkins
========================

`Universum` requires no special integration with `Jenkins`, except for one thing. It is usually launched
as one long step in a single build stage. Because of that, the whole `Universum` log is printed as a plain text
without navigation anchors.

Compare with these:

* When ran locally, all Universum build step logs are stored to separate files instead of printing their
  output to console
* When launched by TeamCity, `Unviersum` uses `service messages
  <https://www.jetbrains.com/help/teamcity/service-messages.html>`__ to increase log readability

To simplify navigating long logs and finding relevant information on build results, we provide a user-friendly
interactive log with collapsible blocks and other features. This log can also be used outside of Jenkins, but
for Jenkins users it adds the missing functionality.

.. warning::

    By default, Jenkins `does not render interactive content <https://www.jenkins.io/doc/book/security/user-content/>`__.
    This means that without changing server settings, interactive features of the generated log will be
    inaccessible when opened directly from Jenkins artifacts.


Here's the list of steps we performed to integrate the interactive log with Jenkins server:

1. :ref:`Add a command line option <jenkins#add_arg>` to generate a self-contained HTML file
2. :ref:`Add a Jenkins plugin <jenkins#plugin>` to integrate a generated log into a Jenkins job
3. :ref:`Set up Resource Root URL <jenkins#resource_url>` to allow Jenkins rendering interactive content
4. :ref:`Configure reverse proxy <jenkins#nginx>` to handle multiple domains interaction


.. _jenkins#add_arg:

Add command line option
-----------------------

To generate a single interactive self-contained HTML file, pass an `--html-log <args.html#Output>`__
option to command line. It will be stored to in project `artifacts <args.html#Artifact\ collection>`__ folder.
Note that the log name can either be specified or left default.

.. note::

    Jenkins jobs do not show any files via web interface if not not specifically configured to do so. Use
    ``archiveArtifacts`` in Pipeline or ``Archive the artifacts`` in `Post-build Actions` to check the file presence
    and contents before next step if needed


.. _jenkins#plugin:

Add a Jenkins plugin
--------------------

A `HTML Publisher <https://plugins.jenkins.io/htmlpublisher/>`__ plugin is a very convenient way to add an HTML report
to a Jenkins job. To use it, you will need to:

1. Install it on server (server restart might be needed to apply changes)
2. Pass the generated log name to plugin configuration as described in manual (https://plugins.jenkins.io/htmlpublisher/)
   via `Post-build Actions` or Pipeline
3. Launch a configured job at least once for the log to be generated
4. Let Jenkins render the interactive content of log (see the next section)


.. _jenkins#resource_url:

Set up Resource Root URL
------------------------

As already mentioned above, due to `Jenkins Content-Security-Policy
<https://www.jenkins.io/doc/book/security/configuring-content-security-policy/>`__ some features of an interactive log
might not work properly, and its contents might be displayed incorrectly.

A recommended way to allow Jenkins server to render interactive user content is to `configure Jenkins to publish
artifacts on a different domain <https://www.jenkins.io/doc/book/security/user-content/#resource-root-url>`__
by changing ``Resource Root URL`` in `Manage Jenkins » Configure System » Serve resource files from another domain`
from ``<main domain>`` to ``<resource domain>`` (e.g. ``my.jenkins.io`` to ``res.my.jenkins.io``).

Note that Jenkins interaction with resource domain, resolved to the same host IP is not done via ``localhost``
network interface. The reason for that is Jenkins requiring some interaction with itself via this domain name.
This means that both ``<main domain>`` and ``<resource domain>`` domain names must be resolved correctly, either
globally (via DNS) or locally on both client and server machines (via ``/etc/hosts`` files). The correctness of
name resolving is checked when saving the changes to this setting; but Jenkins will only show warning, and not
fail if domain name is not resolved.

.. note::

    If main server domain name is not resolved using DNS, ``/etc/hosts`` or any other means, the web-interface
    will only be accessible via IP, and not the name. Because of that, the Jenkins interaction with itself
    via domain name will fail because host name is not passed to the Jenkins server

Here are the symptoms of domain names not resolving correctly:

1. Jenkins warnings when trying to save the updated settings
2. Client inability to access said pages (timeout error)

To set up domain name resolving, add following lines to server ``/ets/hosts`` file::

    127.0.0.1       <main domain>
    <server IP>     <resource domain>

And add the following lines to client ``/ets/hosts`` file::

    <server IP>     <main domain>
    <server IP>     <resource domain>


.. _jenkins#nginx:

Configure reverse proxy
-----------------------

Note that this step is only needed if `Nginx reverse proxy
<https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/>`__ is used.

To understand why these fixes are needed, let's pay more attention to the mechanism of 'another domain', used by
Jenkins. When requesting an artifact, that is served from another domain, user first goes to main Jenkins web
server, that returns a redirection link to acquire a said artifact.

As `specified in docs <https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/#passing-request-headers>`__,
without specification Nginx replaces ``Host`` header with ``$proxy_host``. In this case it changes
``<resource domain>`` to proxy IP specifications. The problem is that without the Host header the Jenkins server
is not able to understand that the request is sent to the resource domain. Therefore it returns the 404 NOT FOUND error.

To pass them correctly, adjust the configuration as instructed in manual mentioned above. Add the following lines
to Nginx configuration file::

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

so that real headers are passed to Jenkins to handle the resource domain magic.

.. note::

    Also you might need to set ``server_name`` to ``<main domain> <resource domain>`` (whitespace separated)
