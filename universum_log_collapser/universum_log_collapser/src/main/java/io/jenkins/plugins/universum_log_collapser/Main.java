package io.jenkins.plugins.universum_log_collapser;

import hudson.MarkupText;

class Main {
    public static void main(String[] args) {
        Annotator annotator = new Annotator();

        for (String line : args[0].split("\n")) {
            MarkupText text = new MarkupText(line);
            annotator = annotator.annotate(null, text);
            System.out.println(text.toString(true));
        }
    }
}
