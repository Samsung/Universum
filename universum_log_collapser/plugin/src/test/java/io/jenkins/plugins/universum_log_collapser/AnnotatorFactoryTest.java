package io.jenkins.plugins.universum_log_collapser;

import org.junit.Test;

import static org.junit.Assert.*;

public class AnnotatorFactoryTest {

    @Test
    public void newInstance() {
        Annotator annotator = new AnnotatorFactory<>().newInstance(null);
        assertEquals(Annotator.class, annotator.getClass());
    }
}
