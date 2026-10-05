"""Zugangsdaten duerfen den GitHub-API-Host bei Download-Redirects nicht verlassen."""
import unittest
import urllib.request
from github_pilot import SichererRedirect


class GitHubTransferTest(unittest.TestCase):
    def test_artefakthost_erhaelt_keinen_github_zugang(self):
        req = urllib.request.Request('https://api.github.com/repos/test/test/actions/logs',
                                     headers={'Authorization': 'Bearer nur-test', 'Accept': 'application/json'})
        weiter = SichererRedirect().redirect_request(req, None, 302, 'Found', {},
                                                     'https://download.example.test/artifact')
        self.assertFalse(weiter.has_header('Authorization'))
        self.assertEqual(weiter.get_header('Accept'), 'application/json')

    def test_gleicher_host_behaelt_zugang(self):
        req = urllib.request.Request('https://api.github.com/alt',
                                     headers={'Authorization': 'Bearer nur-test'})
        weiter = SichererRedirect().redirect_request(req, None, 302, 'Found', {},
                                                     'https://api.github.com/neu')
        self.assertEqual(weiter.get_header('Authorization'), 'Bearer nur-test')

    def test_http_download_wird_abgelehnt(self):
        req = urllib.request.Request('https://api.github.com/alt')
        with self.assertRaises(RuntimeError):
            SichererRedirect().redirect_request(req, None, 302, 'Found', {}, 'http://download.example.test')
