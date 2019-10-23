package io.jenkins.plugins.universum_log_collapser;

import org.junit.Test;

import hudson.MarkupText;
import org.junit.experimental.runners.Enclosed;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;

import java.util.Arrays;

import static org.junit.Assert.*;
import static org.junit.runners.Parameterized.Parameter;
import static org.junit.runners.Parameterized.Parameters;

@RunWith(Enclosed.class)
public class LogActiveTest {

    private static final String logStartLine = "==> Universum 1.2.3 started execution";
    private static final String logEndLine = "==> Universum 1.2.3 finished execution";

    private static final String sectionStartClose = "</label></span><div>";
    private static final String sectionEndClose = "</div><span class=\"nl\"></span>";
    private static final String paddingSpan = "<span style=\"display: inline-block;  width: 4ch;\"></span>";

    public static class nonParametrizedTest {

        @Test
        public void logStartStop() {
            String[] in = new String[] {
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
                    logStartLine,
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
                    logEndLine,
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
                    logStartLine,
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
            };
            String[] out = new String[] {
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
                    replaceWithHtmlEntities(logStartLine),
                    sectionStartOpen(1) + "1. Step name" + sectionStartClose,
                    paddingSpan + " |   step data",
                    paddingSpan + " └ [Success]" + sectionEndClose,
                    replaceWithHtmlEntities(logEndLine),
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
                    replaceWithHtmlEntities(logStartLine),
                    sectionStartOpen(2) + "1. Step name" + sectionStartClose,
                    paddingSpan + " |   step data",
                    paddingSpan + " └ [Success]" + sectionEndClose,
            };
            checkAnnotation(in, out);
        }

        @Test
        public void logNotBroken() {
            String[] in = new String[] {
                    logStartLine,
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
                    "some random line",
                    "1. Step name",
                    " |   step data",
                    " └ [Success]"
            };
            String[] out = new String[] {
                    replaceWithHtmlEntities(logStartLine),
                    sectionStartOpen(1) + "1. Step name" + sectionStartClose,
                    paddingSpan + " |   step data",
                    paddingSpan + " └ [Success]" + sectionEndClose,
                    "some random line",
                    sectionStartOpen(2) + "1. Step name" + sectionStartClose,
                    paddingSpan + " |   step data",
                    paddingSpan + " └ [Success]" + sectionEndClose,
            };
            checkAnnotation(in, out);
        }

        @Test
        public void logBroken() {
            String[] in = new String[] {
                    logStartLine,
                    "1. Step name",
                    " |   step data",
                    "some random line",
                    " └ [Success]",
                    "1. Step name",
                    " |   step data",
                    " └ [Success]"
            };
            String[] out = new String[] {
                    replaceWithHtmlEntities(logStartLine),
                    sectionStartOpen(1) + "1. Step name" + sectionStartClose,
                    paddingSpan + " |   step data",
                    "some random line",
                    " └ [Success]",
                    "1. Step name",
                    " |   step data",
                    " └ [Success]"
            };
            checkAnnotation(in, out);
        }
    }

    @RunWith(Parameterized.class)
    public static class LogStartPositiveTest {

        @Parameter
        public String line;

        @Parameters(name="{0}")
        public static Iterable<String> testData() {
            return Arrays.asList(
                    "==> Universum 1.2.3 started execution",
                    "==> Universum 0.0.0 started execution",
                    "==> Universum 1234.234521.952 started execution"
            );
        }

        @Test
        public void test() {
            String[] in = new String[]{
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
                    line,
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
            };
            String[] out = new String[] {
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
                    replaceWithHtmlEntities(line),
                    sectionStartOpen(1) + "1. Step name" + sectionStartClose,
                    paddingSpan + " |   step data",
                    paddingSpan + " └ [Success]" + sectionEndClose,
            };
            checkAnnotation(in, out);
        }
    }

    @RunWith(Parameterized.class)
    public static class LogStartNegativeTest {

        @Parameter
        public String line;

        @Parameters(name="{0}")
        public static Iterable<String> testData() {
            return Arrays.asList(
                    "==> Universum 1.2.3 finished execution",
                    " ==> Universum 1.2.3 started execution",
                    "=< Universum 1.2.3 started execution",
                    "==> universum 1.2.3 started execution",
                    "==> Universum 1.2 started execution",
                    "==> Universum 1.2 started execution now"
            );
        }

        @Test
        public void test() {
            String[] in = new String[]{
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
                    line,
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
            };
            String[] out = new String[] {
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
                    replaceWithHtmlEntities(line),
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
            };
            checkAnnotation(in, out);
        }
    }

    @RunWith(Parameterized.class)
    public static class LogEndPositiveTest {

        @Parameter
        public String line;

        @Parameters(name="{0}")
        public static Iterable<String> testData() {
            return Arrays.asList(
                    "==> Universum 1.2.3 finished execution",
                    "==> Universum 0.0.0 finished execution",
                    "==> Universum 1234.234521.952 finished execution"
            );
        }

        @Test
        public void test() {
            String[] in = new String[]{
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
                    logStartLine,
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
                    line,
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
            };
            String[] out = new String[] {
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
                    replaceWithHtmlEntities(logStartLine),
                    sectionStartOpen(1) + "1. Step name" + sectionStartClose,
                    paddingSpan + " |   step data",
                    paddingSpan + " └ [Success]" + sectionEndClose,
                    replaceWithHtmlEntities(line),
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
            };
            checkAnnotation(in, out);
        }
    }

    @RunWith(Parameterized.class)
    public static class LogEndNegativeTest {

        @Parameter
        public String line;

        @Parameters(name="{0}")
        public static Iterable<String> testData() {
            return Arrays.asList(
                    "==> Universum 1.2.3 started execution",
                    " ==> Universum 1.2.3 finished execution",
                    "=< Universum 1.2.3 finished execution",
                    "==> universum 1.2.3 finished execution",
                    "==> Universum 1.2 finished execution",
                    "==> Universum 1.2 finished execution now"
            );
        }

        @Test
        public void test() {
            String[] in = new String[]{
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
                    logStartLine,
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
                    line,
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
            };
            String[] out = new String[] {
                    "1. Step name",
                    " |   step data",
                    " └ [Success]",
                    replaceWithHtmlEntities(logStartLine),
                    sectionStartOpen(1) + "1. Step name" + sectionStartClose,
                    paddingSpan + " |   step data",
                    paddingSpan + " └ [Success]" + sectionEndClose,
                    replaceWithHtmlEntities(line),
                    sectionStartOpen(2) + "1. Step name" + sectionStartClose,
                    paddingSpan + " |   step data",
                    paddingSpan + " └ [Success]" + sectionEndClose,
            };
            checkAnnotation(in, out);
        }
    }

    @RunWith(Parameterized.class)
    public static class JobFinishedPositiveTest {

        @Parameter
        public String line;

        @Parameters(name="{0}")
        public static Iterable<String> testData() {
            // https://javadoc.jenkins-ci.org/hudson/model/Result.html
            return Arrays.asList(
                    "Finished: SUCCESS",
                    "Finished: ABORTED",
                    "Finished: FAILURE",
                    "Finished: NOT_BUILT",
                    "Finished: UNSTABLE"
            );
        }

        @Test
        public void test() {
            String[] in = new String[]{
                    line,
                    logStartLine,
                    line
            };
            String finishColoringIframe = "<iframe onload=\"finishColoring()\" style=\"display:none\"></iframe>";
            String[] out = new String[] {
                    line + finishColoringIframe,
                    replaceWithHtmlEntities(logStartLine),
                    line + finishColoringIframe
            };
            checkAnnotation(in, out);
        }
    }

    @RunWith(Parameterized.class)
    public static class JobFinishedNegativeTest {

        @Parameter
        public String line;

        @Parameters(name="{0}")
        public static Iterable<String> testData() {
            return Arrays.asList(
                    " Finished: SUCCESS",
                    "Finished: SUCCESS ",
                    "Finished: ",
                    "finish",
                    "Finished: success"
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
                    line
            };
            checkAnnotation(in, out);
        }
    }


    private static void checkAnnotation(String[] in, String[] out) {
        assertEquals(in.length, out.length);

        Annotator annotator = new Annotator(null);
        for (int i = 0; i < in.length; i++) {
            MarkupText text = new MarkupText(in[i]);
            Annotator result = annotator.annotate(null, text);

            assertEquals(annotator, result);
            System.out.println(out[i]);
            System.out.println(text.toString(true));
            assertEquals(out[i], text.toString(true));
        }
    }

    private static String replaceWithHtmlEntities(String line) {
        return line.replaceAll(">", "&gt;").replaceAll("<", "&lt;");
    }

    private static String sectionStartOpen(int idNum) {
        return String.format("<input type=\"checkbox\" id=\"hide-block-%d\" class=\"hide\"/>", idNum) +
                String.format("<label for=\"hide-block-%d\">", idNum) +
                "<span class=\"sectionLbl\">";
    }
}
