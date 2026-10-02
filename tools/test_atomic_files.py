import unittest
from unittest.mock import Mock,patch
from atomic_files import replace_with_retry

class AtomicFileTests(unittest.TestCase):
    def test_transient_windows_sharing_error_is_retried(self):
        error=PermissionError('temporarily locked');error.winerror=5
        temporary=Mock();temporary.replace.side_effect=[error,None]
        with patch('atomic_files.time.sleep') as wait:replace_with_retry(temporary,'target')
        self.assertEqual(temporary.replace.call_count,2);wait.assert_called_once_with(0.05)

    def test_other_permission_failures_propagate_immediately(self):
        temporary=Mock();temporary.replace.side_effect=PermissionError('denied')
        with patch('atomic_files.time.sleep') as wait:
            with self.assertRaises(PermissionError):replace_with_retry(temporary,'target')
        self.assertEqual(temporary.replace.call_count,1);wait.assert_not_called()

    def test_windows_retries_are_bounded(self):
        error=PermissionError('locked');error.winerror=32
        temporary=Mock();temporary.replace.side_effect=error
        with patch('atomic_files.time.sleep') as wait:
            with self.assertRaises(PermissionError):replace_with_retry(temporary,'target')
        self.assertEqual(temporary.replace.call_count,7)
        self.assertAlmostEqual(sum(c.args[0] for c in wait.call_args_list),3.15)

if __name__=='__main__':unittest.main()
