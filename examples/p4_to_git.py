#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import
import argparse
from P4 import P4
from universum import __main__


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--p4-port")
    parser.add_argument("--p4-user")
    parser.add_argument("--p4-password")
    parser.add_argument("--p4-client")
    parser.add_argument("--p4-depot-path")
    parser.add_argument("--p4-client-root")
    parser.add_argument("--git-repo")
    parser.add_argument("--git-user")
    parser.add_argument("--git-email")
    args = parser.parse_args()

    p4 = P4()

    p4.port = args.p4_port
    p4.user = args.p4_user
    p4.password = args.p4_password
    client_name = args.p4_client

    p4.connect()

    depot_path = args.p4_depot_path

    client = p4.fetch_client(client_name)
    client["Root"] = args.p4_client_root
    client["View"] = [depot_path + " //" + client_name + "/..."]
    p4.save_client(client)
    p4.client = client_name

    changes = p4.run_changes("-s", "submitted", depot_path)
    cl_list = []
    for change in changes:
        cl_list.append(change["change"])
    
    for cl in reversed(cl_list):
        line = depot_path + '@' + cl
        p4.run_sync("-f", line)
    
        __main__.main(["submit",
                        "-ot", "term",
                        "-vt", "git",
                        "-cm", p4.run_describe(cl)[0]['desc'],
                        "-gu", args.git_user,
                        "-ge", args.git_email,
                        "-pr", args.git_repo,
                        "-gr", "file://" + args.git_repo,
                        "-grs", "master"])

    p4.delete_client(client_name)


if __name__ == "__main__":
    main()
