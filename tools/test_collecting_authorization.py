"""Standing publication authority must not weaken collection or access checks."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / 'site/collecting-policy.json').read_text(encoding='utf-8'))


class CollectingAuthorizationTests(unittest.TestCase):
    def test_agent_review_replaces_per_batch_user_approval(self):
        authority = POLICY['publicationAuthority']
        self.assertEqual(authority['authorizedBy'], 'direct-user-standing-authorization')
        self.assertEqual(authority['reviewer'], 'maintaining-agent')
        self.assertFalse(authority['requiresPerBatchUserApproval'])
        self.assertFalse(authority['requiresPerSourceUserApproval'])
        self.assertTrue(authority['releaseChecksRequired'])
        self.assertEqual(set(authority['reviewRequirements']), {
            'provenance', 'source-established date', 'model-to-output mapping',
            'real displayable media', 'deduplication', 'rights', 'safety',
        })
        self.assertIn('verified subsets', authority['readySubsetPolicy'])
        self.assertIn('user direction', authority['scopeExpansion'])

    def test_chrome_fallback_preserves_access_boundaries(self):
        access = POLICY['restrictedRetrievalFallback']
        self.assertEqual(access['browser'], 'user-already-signed-in-chrome')
        self.assertFalse(access['requiresAdditionalUserApproval'])
        for key in ['publicContentOnly', 'readOnly', 'backgroundTabs']:
            self.assertTrue(access[key])
        for key in ['collectCredentialsOrAccountData', 'bypassAccessControls']:
            self.assertFalse(access[key])
        self.assertIn('continue reachable candidates', access['onLoginChallengeOrConnectionFailure'])

    def test_scope_and_reference_exclusion_are_preserved(self):
        self.assertTrue(POLICY['allMediaTypes'])
        self.assertEqual(POLICY['dateRange'], 'all source-established dates')
        self.assertTrue(POLICY['referenceOnlyExcluded'])
        self.assertFalse(POLICY['allowRedraw'])
        self.assertFalse(POLICY['compositeInMainLists'])


if __name__ == '__main__':
    unittest.main()
