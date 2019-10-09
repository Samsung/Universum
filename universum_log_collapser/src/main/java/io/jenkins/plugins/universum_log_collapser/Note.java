package io.jenkins.plugins.universum_log_collapser;

import hudson.Extension;
import hudson.MarkupText;
import hudson.console.ConsoleAnnotationDescriptor;
import hudson.console.ConsoleNote;

public class Note<T> extends ConsoleNote<T> {
    
    private static final long serialVersionUID = 1L;

    public Annotator annotate(T context, MarkupText text, int charPos) {
        return null;
    }

    // Extension point to connect plugin style.css to Console Ouput HTML page
    @Extension
    public static final class Descriptor extends ConsoleAnnotationDescriptor {}
}
