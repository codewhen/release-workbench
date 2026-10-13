"""A form-selected unittest runner that rejects empty test discovery."""
import sys,unittest

def main():
 suite=unittest.defaultTestLoader.discover(sys.argv[1] if len(sys.argv)>1 else '.')
 if not suite.countTestCases():
  print('No tests found. Choose the test folder before running this card.',file=sys.stderr);return 1
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 return 0 if result.wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(main())
