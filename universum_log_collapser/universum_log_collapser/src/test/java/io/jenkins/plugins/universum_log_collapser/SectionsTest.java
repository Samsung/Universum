package io.jenkins.plugins.universum_log_collapser;

import org.junit.Test;
import org.junit.experimental.runners.Enclosed;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;

import java.util.Arrays;

@RunWith(Enclosed.class)
public class SectionsTest extends TestSuite {

    public static class nonParametrizedTest {

        @Test
        public void ignoredSection() {
            String[] in = new String[] {
                    logStartLine,
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
                    "3. Reporting build result",
                    " | 1. Step name - Success",
                    " | 2. Step name2 - Failed",
                    " └ [Success]",
                    "5. Step name",
                    " |   step data",
                    " └ [Success]"

            };
            String[] out = new String[] {
                    replaceWithHtmlEntities(logStartLine),
                    sectionStartOpen(1) + "1. Step name" + sectionStartClose,
                    paddingSpan + " |   step data",
                    paddingSpan + " └ [Success]" + sectionEndClose,
                    sectionStartOpen(2) + "3. Reporting build result" + sectionStartClose,
                    paddingSpan + " | 1. Step name - Success",
                    paddingSpan + " | 2. Step name2 - Failed",
                    paddingSpan + " └ [Success]" + sectionEndClose,
                    sectionStartOpen(3) + "5. Step name" + sectionStartClose,
                    paddingSpan + " |   step data",
                    paddingSpan + " └ [Success]" + sectionEndClose,
            };
            checkAnnotation(in, out);
        }

        @Test
        public void ignoredSectionTimestamps() {
            String[] in = new String[] {
                    timestampCorrect + " " + logStartLine,
                    timestampCorrect + " 1. Step name",
                    timestampCorrect + "  |   step data",
                    timestampCorrect + "  └ [Success]",
                    timestampCorrect + " 3. Reporting build result",
                    timestampCorrect + "  | 1. Step name - Success",
                    timestampCorrect + "  | 2. Step name2 - Failed",
                    timestampCorrect + "  └ [Success]",
                    timestampCorrect + " 5. Step name",
                    timestampCorrect + "  |   step data",
                    timestampCorrect + "  └ [Success]"

            };
            String[] out = new String[] {
                    replaceWithHtmlEntities(timestampCorrect + " " + logStartLine),
                    timestampCorrect + " " + sectionStartOpen(1) + "1. Step name" + sectionStartClose,
                    timestampCorrect + " " + paddingSpan + " |   step data",
                    timestampCorrect + " " + paddingSpan + " └ [Success]" + sectionEndClose,
                    timestampCorrect + " " + sectionStartOpen(2) + "3. Reporting build result" + sectionStartClose,
                    timestampCorrect + " " + paddingSpan + " | 1. Step name - Success",
                    timestampCorrect + " " + paddingSpan + " | 2. Step name2 - Failed",
                    timestampCorrect + " " + paddingSpan + " └ [Success]" + sectionEndClose,
                    timestampCorrect + " " + sectionStartOpen(3) + "5. Step name" + sectionStartClose,
                    timestampCorrect + " " + paddingSpan + " |   step data",
                    timestampCorrect + " " + paddingSpan + " └ [Success]" + sectionEndClose,
            };
            checkAnnotation(in, out);
        }

        @Test
        public void pipelineFix() {
            String[] in = new String[] {
                    logStartLine,
                    "2. Step name",
                    " |   step data",
                    " └ [Success]",

            };
            String[] out = new String[] {
                    replaceWithHtmlEntities(logStartLine),
                    pipelineJsFix + sectionStartOpen(1) + "2. Step name" + sectionStartClose,
                    paddingSpan + " |   step data",
                    paddingSpan + " └ [Success]" + sectionEndClose,
            };
            checkAnnotation(in, out);
        }

        @Test
        public void pipelineFixTimestamps() {
            String[] in = new String[] {
                    timestampCorrect + " " + logStartLine,
                    timestampCorrect + " 2. Step name",
                    timestampCorrect + "  |   step data",
                    timestampCorrect + "  └ [Success]",

            };
            String[] out = new String[] {
                    replaceWithHtmlEntities(timestampCorrect + " " + logStartLine),
                    pipelineJsFix + timestampCorrect + " " + sectionStartOpen(1) + "2. Step name" + sectionStartClose,
                    timestampCorrect + " " + paddingSpan + " |   step data",
                    timestampCorrect + " " + paddingSpan + " └ [Success]" + sectionEndClose,
            };
            checkAnnotation(in, out);
        }

        @Test
        public void sectionsNesting() {
            String[] in = new String[] {
                    logStartLine,
                    "1. Step1 name",
                    " | step1 data",
                    " | 1.1. Step11 name",
                    " |    | step11 data",
                    " |    | 1.1.1. Step111 name",
                    " |    |      | step111 data",
                    " |    |      └ [Success]",
                    " |    | step11 data",
                    " |    └ [Success]",
                    " | step1 data",
                    " └ [Success]"
            };
            String[] out = new String[] {
                    replaceWithHtmlEntities(logStartLine),
                    sectionStartOpen(1) + "1. Step1 name" + sectionStartClose,
                    paddingSpan + " | step1 data",
                    paddingSpan + sectionInputLabel(2) +  " | " + sectionSpan + "1.1. Step11 name" + sectionStartClose,
                    paddingSpan + " | " + paddingSpan + "   | step11 data",
                    paddingSpan + sectionInputLabel(3) +  " | " + paddingSpan +   "   | " + sectionSpan + "1.1.1. Step111 name" + sectionStartClose,
                    paddingSpan + " | " + paddingSpan + "   | " + paddingSpan + "     | step111 data",
                    paddingSpan + " | " + paddingSpan + "   | " + paddingSpan + "     └ [Success]" + sectionEndClose,
                    paddingSpan + " | " + paddingSpan + "   | step11 data",
                    paddingSpan + " | " + paddingSpan + "   └ [Success]" + sectionEndClose,
                    paddingSpan + " | step1 data",
                    paddingSpan + " └ [Success]" + sectionEndClose,
            };
            checkAnnotation(in, out);
        }

        @Test
        public void sectionStartTimestampPositive() {
            String[] in = new String[]{
                logStartLine,
                timestampCorrect + " 1. Section"
            };
            String[] out = new String[] {
                    replaceWithHtmlEntities(logStartLine),
                    timestampCorrect + " " + sectionStartOpen(1) + "1. Section" + sectionStartClose
            };
            checkAnnotation(in, out);
        }
    }

    @RunWith(Parameterized.class)
    public static class SectionStartPositiveTest {

        @Parameterized.Parameter
        public String line;

        @Parameterized.Parameters(name="{0}")
        public static Iterable<String> testData() {
            return Arrays.asList(
                    "1. Section",
                    "2222222. Section",
                    "3.Section",
                    "4.",
                    "5. Some long name"
            );
        }

        @Test
        public void test() {
            String[] in = new String[]{
                    logStartLine,
                    line,
            };
            String[] out = new String[] {
                    replaceWithHtmlEntities(logStartLine),
                    sectionStartOpen(1) + line + sectionStartClose,
            };
            checkAnnotation(in, out);
        }
    }

    @RunWith(Parameterized.class)
    public static class SectionStartNegativeTest {

        @Parameterized.Parameter
        public String line;

        @Parameterized.Parameters(name="{0}")
        public static Iterable<String> testData() {
            return Arrays.asList(
                    "+++ 1. Section",
                    "asdf | 1. Section",
                    ". Section",
                    "3 Section",
                    "4asdfas",
                    timestampCorrect + "1. Section",
                    timestampEmpty + " 1. Section",
                    timestampNoBraces + " 1. Section",
                    timestampIllegalSymbols + " 1. Section"
            );
        }

        @Test
        public void test() {
            String[] in = new String[]{
                    logStartLine,
                    line,
            };
            String[] out = new String[] {
                    replaceWithHtmlEntities(logStartLine),
                    line,
            };
            checkAnnotation(in, out);
        }
    }

    @RunWith(Parameterized.class)
    public static class SectionEndPositiveTest {

        @Parameterized.Parameter
        public String line;

        @Parameterized.Parameters(name="{0}")
        public static Iterable<String> testData() {
            return Arrays.asList(
                    "└ [result]",
                    "  || └ [result]",
                    "└ [ResULT]",
                    "└ [r]",
                    "└ [result] some random text  ",
                    "└ some random text [result]",
                    timestampCorrect + " └ [result]"
            );
        }

        @Test
        public void test() {
            String[] in = new String[]{
                    logStartLine,
                    line,
            };
            String[] out = new String[] {
                    replaceWithHtmlEntities(logStartLine),
                    line + sectionEndClose,
            };
            checkAnnotation(in, out);
        }
    }

    @RunWith(Parameterized.class)
    public static class SectionEndNegativeTest {

        @Parameterized.Parameter
        public String line;

        @Parameterized.Parameters(name="{0}")
        public static Iterable<String> testData() {
            return Arrays.asList(
                    "-└ [result]",
                    "*| └ [result]",
                    "  - [result]",
                    "└ [result1]",
                    "└ []",
                    "└ [result",
                    "└ result]",
                    "└ result",
                    timestampCorrect + "└ [result]",
                    timestampEmpty + " └ [result]",
                    timestampNoBraces + " └ [result]",
                    timestampIllegalSymbols + " └ [result]"
            );
        }

        @Test
        public void test() {
            String[] in = new String[]{
                    logStartLine,
                    line,
            };
            String[] out = new String[] {
                    replaceWithHtmlEntities(logStartLine),
                    line,
            };
            checkAnnotation(in, out);
        }
    }

    @RunWith(Parameterized.class)
    public static class FailedSectionPositiveTest {

        @Parameterized.Parameter
        public String line;

        @Parameterized.Parameters(name="{0}")
        public static Iterable<String> testData() {
            return Arrays.asList(
                    "└ [Failed]",
                    "  || └ [Failed]",
                    "└ [Failed] some random text  ",
                    timestampCorrect + " └ [Failed]"
            );
        }

        @Test
        public void test() {
            String[] in = new String[]{
                    logStartLine,
                    line
            };

            String failedResultOpen = "<span class=\"failed_result\">";
            String failedResultClose = "</span>";
            String[] out = new String[] {
                    replaceWithHtmlEntities(logStartLine),
                    line + failedResultOpen + failedResultClose + sectionEndClose,
            };
            checkAnnotation(in, out);
        }
    }

    @RunWith(Parameterized.class)
    public static class FailedSectionNegativeTest {

        @Parameterized.Parameter
        public String line;

        @Parameterized.Parameters(name="{0}")
        public static Iterable<String> testData() {
            return Arrays.asList(
                    "└ [failed]",
                    "└ [Fail]",
                    "└ [FAIL]",
                    "└ [FAILED]"
            );  
        }

        @Test
        public void test() {
            String[] in = new String[]{
                    logStartLine,
                    line
            };

            String[] out = new String[] {
                    replaceWithHtmlEntities(logStartLine),
                    line + sectionEndClose,
            };
            checkAnnotation(in, out);
        }
    }
}
