package io.jenkins.plugins.universum_log_collapser;

import hudson.MarkupText;
import hudson.console.ConsoleAnnotator;

import java.util.logging.*;
import java.util.regex.Pattern;
import java.util.regex.Matcher;
import java.util.List;
import java.io.Serializable;
import java.util.ArrayList;

class PaddingItem implements Serializable {
    public int position;
    public int spacesNumber;

    public PaddingItem(int p, int s) {
        position = p;
        spacesNumber = s;
    }
}

public class Annotator extends ConsoleAnnotator<Object> {

    private static final long serialVersionUID = 1L;
    private static final Logger logger = Logger.getLogger(Annotator.class.getName());

    private int labelsCnt = 1;
    private boolean isIgnoredSection = false;
    private List<PaddingItem> paddings = new ArrayList<>();
    private boolean universumLogActive = false;

    private Pattern sectionStartPattern = Pattern.compile("(^[|\\s]*)(\\d+\\.).*");
    private Pattern sectionEndPattern = Pattern.compile("^[|\\s]*└.*\\[.+\\].*");
    private Pattern sectionFailPattern = Pattern.compile("^[|\\s]*└.*\\[Failed\\].*");
    /*
        "Reporting build result" section is showing summarized results of all
        build steps. Each line of this section is treated as section start, but
        have no content. That's why we are just collapsing all this section 
        content without content processing.
     */
    private Pattern ignoredSectionPattern = Pattern.compile(".*Reporting build result.*");
    private Pattern universumLogStartPattern = Pattern.compile("^==&gt; Universum \\d+\\.\\d+\\.\\d+ started execution$");
    private Pattern universumLogEndPattern = Pattern.compile("^==> Universum \\d+\\.\\d+\\.\\d+ finished execution$");
    private Pattern jenkinsLogEndPattern = Pattern.compile(".*Finished: .*");
    private Pattern healthyLogPattern = Pattern.compile("^\\s+[\\|└]\\s+.*");

    public Annotator(Object context) {}

    /*
    Before:
      1. Preparing repository
       |   ==> Adding file /var/lib/jenkins/workspace/universum_job/artifacts/REPOSITORY_STATE.txt to artifacts...
       |   1.1. Copying sources to working directory
       |      |   ==> Moving sources to '/var/lib/jenkins/workspace/universum_job/temp'...
       |      └ [Success]
       |   
       └ [Success]

    After:
        <input type="checkbox" id="hide-block-1" class="hide">
        <label for="hide-block-1">
            <span class="sectionLbl">
                1. Preparing repository
            </span>
        </label>
        <div>
             |   ==> Adding file /var/lib/jenkins/workspace/universum_job/artifacts/REPOSITORY_STATE.txt to artifacts...
            <input type="checkbox" id="hide-block-2" class="hide">
            <label for="hide-block-2">
                 |   
                <span class="sectionLbl">
                    1.1. Copying sources to working directory
                </span>
            </label>
            <div>
                 |          |   ==> Moving sources to '/var/lib/jenkins/workspace/universum_job/temp'...
                 |          └ [Success]
            </div>
            <span class="nl">
            </span>
             |   
             └ [Success]
        </div>
        <span class="nl">
        </span>
    */
    @Override
    public Annotator annotate(Object context, MarkupText text) {
        String textStr = text.toString(true);
        logger.info(textStr);

        universumLogActive = universumLogActive || universumLogStartPattern.matcher(textStr).find();
        if (!universumLogActive) {
            logger.info("Skip non-universum log");
            return this;
        }

        if (universumLogEndPattern.matcher(textStr).find()) {
            universumLogActive = false;
        }

        for (PaddingItem p : paddings) {
            if (!healthyLogPattern.matcher(textStr).find()) {
                logger.info("Log is broken, identation expected");
                universumLogActive = false;
                return this;
            }
            text.addMarkup(p.position, "<span style=\"display: inline-block; " +
                " width: " + (p.spacesNumber + 2) + "ch;\"></span>");
        }
        
        Matcher sectionStartMatcher = sectionStartPattern.matcher(textStr);
        if (sectionStartMatcher.find()) {
            processSectionStart(text, sectionStartMatcher);
            return this;
        } 
        
        Matcher sectionEndMatcher = sectionEndPattern.matcher(textStr);
        if (sectionEndMatcher.find()) {
            processSectionEnd(text, sectionFailPattern.matcher(textStr));
            return this;
        }

        Matcher jenkinsLogEndMatcher = jenkinsLogEndPattern.matcher(textStr);
        if (jenkinsLogEndMatcher.find()) {
            text.addMarkup(text.length(), "<iframe onload=\"finishColoring()\" style=\"display:none\"></iframe>");
            return this;
        }

        return this;
    }


    private void processSectionStart(MarkupText text, Matcher sectionStartMatcher) {
        if (isIgnoredSection) {
            logger.info("Skip ignored section");
            return;
        }
        
        logger.info("Section start found");
        if (ignoredSectionPattern.matcher(text.toString(true)).find()) {
            isIgnoredSection = true;
        }
        
        int sectionNumberStartPosition = sectionStartMatcher.end(1);
        int sectionNumberEndPosition = sectionStartMatcher.end(2);
        paddings.add(new PaddingItem(sectionNumberStartPosition, 
            sectionNumberEndPosition - sectionNumberStartPosition));

        String inputId = "hide-block-" + labelsCnt++;
        text.addMarkup(0, "<input type=\"checkbox\" id=\"" + inputId + 
            "\" class=\"hide\"/><label for=\"" + inputId + "\">");
        text.addMarkup(sectionNumberStartPosition, "<span class=\"sectionLbl\">");
        text.addMarkup(text.length(), "</label></span><div>");
    }

    private void processSectionEnd(MarkupText text, Matcher sectionFailMatcher) {
        logger.info("Section end found");
        paddings.remove(paddings.size() - 1);
        
        if (sectionFailMatcher.find()) {
            logger.info("Failed section found");
            text.addMarkup(0, "<span class=\"failed_result\">");
            text.addMarkup(text.length(), "</span>");
        }
        text.addMarkup(text.length(), "</div><span class=\"nl\"></span>");

        isIgnoredSection = false;
    }
}
