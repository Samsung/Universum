package io.jenkins.plugins.universum_log_collapser;

import hudson.Extension;
import hudson.console.ConsoleAnnotatorFactory;

// Plugin entry point
@Extension
public class AnnotatorFactory<T> extends ConsoleAnnotatorFactory<T> {
    @Override
    public Annotator newInstance(T context) {
        return new Annotator();
    }
}
