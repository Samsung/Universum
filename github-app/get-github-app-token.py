#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import argparse
import github


def get_params():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", "-k", help="private key file")
    parser.add_argument("--integration-id", "-it", help="GitHub application ID (see 'general')")
    parser.add_argument("--installation-id", "-is", help="in-project installation ID (see 'integrations & services')")
    return parser.parse_args()


def main():
    params = get_params()
    with open(params.key) as f:
        private_key = f.read()
    integration = github.GithubIntegration(params.integration_id, private_key)
    auth_obj = integration.get_access_token(params.installation_id)
    print auth_obj.token


if __name__ == "__main__":
    main()
