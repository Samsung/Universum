package io.jenkins.plugins.universum_log_collapser;

import hudson.MarkupText;

import static org.junit.Assert.assertEquals;

class TestSuite {

    static final String logStartLine = "==> Universum 1.2.3 started execution";
    static final String logEndLine = "==> Universum 1.2.3 finished execution";

    static final String sectionStartClose = "</span></label><div>";
    static final String sectionEndClose = "</div><span class=\"nl\"></span>";
    static final String sectionSpan = "<span class=\"sectionLbl\">";
    static final String paddingSpan = "<span style=\"display: inline-block;  width: 4ch;\"></span>";
    static final String pipelineJsFix = "<iframe onload=\"fix_pipeline()\" style=\"display:none\"></iframe>";

    static final String timestampCorrect = "[2020-01-10T07:47:57.954Z]";
    static final String timestampEmpty = "[]";
    static final String timestampNoBraces = "2020-01-10T07:47:57.954Z";
    static final String timestampIllegalSymbols = "[2020=01=10T07:47:57,954Z]";


    static void checkAnnotation(String[] in, String[] out) {
        assertEquals(in.length, out.length);

        Annotator annotator = new Annotator();
        for (int i = 0; i < in.length; i++) {
            MarkupText text = new MarkupText(in[i]);
            Annotator result = annotator.annotate(null, text);

            assertEquals(annotator, result);
            System.out.println(out[i]);
            System.out.println(text.toString(true));
            assertEquals(out[i], text.toString(true));
        }
    }

    static String replaceWithHtmlEntities(String line) {
        return line.replaceAll(">", "&gt;").replaceAll("<", "&lt;");
    }

    static String sectionStartOpen(int idNum) {
        return sectionInputLabel(idNum) + sectionSpan;
    }

    static String sectionInputLabel(int idNum) {
        return String.format("<input type=\"checkbox\" id=\"hide-block-%d\" class=\"hide\"/>", idNum) +
                String.format("<label for=\"hide-block-%d\">", idNum);
    }
}
