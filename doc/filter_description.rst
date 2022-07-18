
| Allows to filter which steps to execute during launch.
 String value representing single filter or a set of filters separated by '**:**'.
 To define exclude pattern use '**!**' symbol at the beginning of the pattern.
|
| A Universum step match specified pattern when 'filter' is a substring of step 'name'.
 This functionality is similar to 'boosttest' and 'gtest' filtering, except special characters
 (like '*', '?', etc.) are ignored.
|
| Examples:
| * -f='run test'               - run only steps that contain 'run test' substring in their names
| * -f='!run test'              - run all steps except those containing 'run test' substring in their
 names
| * -f='test 1:test 2'          - run all steps with 'test 1' OR 'test 2' substring in their names
| * -f='test 1:!unit test 1'    - run all steps with 'test 1' substring in their names except those
 containing 'unit test 1'
