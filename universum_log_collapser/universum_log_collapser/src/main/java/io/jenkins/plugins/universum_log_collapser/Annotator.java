package io.jenkins.plugins.universum_log_collapser;

import hudson.MarkupText;
import hudson.console.ConsoleAnnotator;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.logging.Logger;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

class PaddingItem implements Serializable {
    int position;
    int spacesNumber;

    PaddingItem(int p, int s) {
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

    private String patternOptional = "(\\[[\\w-:\\.]+\\] )?";
    private Pattern sectionStartPattern = Pattern.compile("^" + patternOptional + "([|\\s]*)(\\d+)\\..*");
    private Pattern sectionEndPattern = Pattern.compile("^" + patternOptional + "[|\\s]*└.*\\[[a-zA-Z]+].*");
    private Pattern sectionFailPattern = Pattern.compile("^" + patternOptional + "[|\\s]*└.*\\[Failed].*");
    /*
        "Reporting build result" section is showing summarized results of all
        build steps. Each line of this section is treated as section start, but
        have no content. That's why we are just collapsing all this section 
        content without content processing.
     */
    private Pattern ignoredSectionPattern = Pattern.compile(".*Reporting build result.*");
    private Pattern universumLogStartPattern = Pattern.compile("^" + patternOptional + "==> Universum \\d+\\.\\d+\\.\\d+ started execution$");
    private Pattern universumLogEndPattern = Pattern.compile("^" + patternOptional + "==> Universum \\d+\\.\\d+\\.\\d+ finished execution$");
    private Pattern jenkinsLogEndPattern = Pattern.compile("^" + patternOptional + "Finished: [A-Z_]+$");
    private Pattern healthyLogPattern = Pattern.compile("^" + patternOptional + "\\s+[|└]\\s+.*");

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
        String textStr = text.getText();
        logger.info(textStr);

        Matcher jenkinsLogEndMatcher = jenkinsLogEndPattern.matcher(textStr);
        if (jenkinsLogEndMatcher.find()) {
            logger.info("Jenkins log end found");
            text.addMarkup(text.length(), "<iframe onload=\"finishColoring()\" style=\"display:none\"></iframe>");
        }

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
                logger.info("Log is broken, indentation expected");
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
        
        // Fix first section, broken by pipeline execution. See JS sources for details.
        if (sectionStartMatcher.group(3).equals("2")) {
            text.addMarkup(0, "<iframe onload=\"fix_pipeline()\" style=\"display:none\"></iframe>");
        }
        
        int sectionNumberStartPosition = sectionStartMatcher.end(2);
        int sectionNumberEndPosition = sectionStartMatcher.end(3) + 1;
        paddings.add(new PaddingItem(sectionNumberStartPosition, 
            sectionNumberEndPosition - sectionNumberStartPosition));

        String inputId = "hide-block-" + labelsCnt++;

        int checkboxInsertPosition = sectionStartMatcher.end(1);
        // if timestamp is absent, position is -1
        checkboxInsertPosition = (checkboxInsertPosition < 0) ? 0 : checkboxInsertPosition;
        logger.info("insert position: " + checkboxInsertPosition);

        text.addMarkup(checkboxInsertPosition, "<input type=\"checkbox\" id=\"" + inputId + 
            "\" class=\"hide\"/><label for=\"" + inputId + "\">");
        text.addMarkup(sectionNumberStartPosition, "<span class=\"sectionLbl\">");
        text.addMarkup(text.length(), "</span></label><div>");
    }

    private void processSectionEnd(MarkupText text, Matcher sectionFailMatcher) {
        logger.info("Section end found");
        if (paddings.size() > 0) {
            paddings.remove(paddings.size() - 1);
        }

        if (sectionFailMatcher.find()) {
            logger.info("Failed section found");
            text.addMarkup(sectionFailMatcher.end(0), "<span class=\"failed_result\">");
            text.addMarkup(text.length(), "</span>");
        }
        text.addMarkup(text.length(), "</div><span class=\"nl\"></span>");

        isIgnoredSection = false;
    }
}
