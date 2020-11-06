var coloringTimeoutMilliSeconds = 250;
var timerId = setInterval(colorFailedSections, coloringTimeoutMilliSeconds);

function colorLblsAscendant(el) {
    if (el == null) {
        return;
    }
    var sectionLbl = el.getElementsByClassName("sectionLbl")[0];
    sectionLbl.style.color = "red";
    var innerSpans = sectionLbl.getElementsByTagName("span");
    if (innerSpans.length > 0) {
        innerSpans[0].style.cssText = "color:red !important";
    }
    sectionLbl.parentElement.previousSibling.checked = true; // expand failed section
    var parent = el.parentNode;
    if (parent.className != "console-output") {
        colorLblsAscendant(parent.previousSibling);
    }
}

function colorFailedSections() {
    fetchNext = myFetchNext;

    var results = document.getElementsByClassName("failed_result");
    /*
    `i` should not be incremented, because array itself becomes smaller when `failed_result` class changed to 
    `failed_result_handled`.
    https://developer.mozilla.org/en-US/docs/Web/API/Document/getElementsByClassName
    Warning: This is a live array. Changes in the DOM will reflect in the array as the changes occur. 
    If an element selected by this array no longer qualifies for the selector, it will automatically be removed. 
    Be aware of this for iteration purposes.
    */
    for (var i = 0; i < results.length; /*intentionally nothing*/) {
        var element = results[i];
        colorLblsAscendant(element.parentNode.previousSibling);
        element.className = "failed_result_handled";
    }
}

function finishColoring() {
    clearInterval(timerId);
    setTimeout(colorFailedSections, coloringTimeoutMilliSeconds);
}

/*
When Universum is executed using pipeline "sh", pipeline span brokes first section collapse/expand mechanism.
Finding target <span> element and simply move a content out from tag body.
*/
function fix_pipeline() {
    var spans = document.getElementsByTagName("span");
    var logStartRegexp = new RegExp("==&gt; Universum \\d+\\.\\d+\\.\\d+ started execution");
    var classNameRegexp = new RegExp("^pipeline-node-\\d+$");
    
    for (var i = 0; i < spans.length; i++) {
        var el = spans[i];
        if ((logStartRegexp.exec(el.innerHTML) == undefined) || (classNameRegexp.exec(el.className) == undefined)) {
            continue;
        }

        el.nextSibling.insertAdjacentHTML("beforebegin", el.innerHTML);
        el.innerHTML = "";
        break;
    }
}


/*
Overrided implementation of Jenkins fetchNext() function.
It's called when Universum step takes long time and console output is splitted to several <pre> tags instead of one.
e: global <pre> tag
href: URL to send request for further log
text: further log, received from URL
*/
var myFetchNext = function(e, href) {
    var headers = {};
    if (e.consoleAnnotator != undefined) {
        headers["X-ConsoleAnnotator"] = e.consoleAnnotator;
    }

	new Ajax.Request(href, {method: "post", parameters: {"start":e.fetchedBytes},
        requestHeaders: headers, onComplete: function(rsp,_) {
        var stickToBottom = scroller.isSticking();
        var text = rsp.responseText;
        if(text != "") {
            /*
            Following code was replaced by customTextHandle() call:
            var p = document.createElement("DIV");
            e.appendChild(p);
            if (p.outerHTML) {
                p.outerHTML = '<pre>' + text + '</pre>';
                p = e.lastChild;
            } else {
                p.innerHTML = text;
            }
            Behaviour.applySubtree(p);
            */
            customTextHandle(e, text);
            ElementResizeTracker.fireResizeCheck();
            if(stickToBottom) {
                scroller.scrollToBottom();
            }
        }

        e.fetchedBytes     = rsp.getResponseHeader("X-Text-Size");
        e.consoleAnnotator = rsp.getResponseHeader("X-ConsoleAnnotator");
	    if(rsp.getResponseHeader("X-More-Data") == "true") {
            setTimeout(function() {fetchNext(e,href);}, 1000);
        } else {
            $("spinner").style.display = "none";
        }
    	}
	});
}

/*
Find last closed tags in text, which already exists on page
For each closed tag:
    - find tag element on page
    - find closed tag position in received text
    - append received tag content to existing tag element
*/
function customTextHandle(e, text) {
    var lastClosedTags = e.innerHTML.match(new RegExp("(<\/\\w+>)+$", "g")); // e.g. </div></div></pre>
    var closedTagsArr = lastClosedTags[0].match(new RegExp("<\/\\w+>", "g")); // split to array

    /*
    Key - tag name. Value - element object.
    Used to find proper element to append a text in case of nested tags with the same name.
    */
    var tagsElementMap = new Map();
    var currTextPosition = 0;
    for (var i = 0; i < closedTagsArr.length; i++) {
        var tagName = closedTagsArr[i].match(new RegExp("<\/(\\w+)>"))[1]; // "</div>" or "<div>" => "div"
        var tagElements = e.getElementsByTagName(tagName);
        var tagPosition = findClosedTagPosition(text, tagName, currTextPosition);

        var element = null;
        var closedElement = tagsElementMap.get(tagName);
        if (closedElement != undefined) {
            // if we already handled one <div>, get its parent
            element = closedElement.parentElement;
        } else {
            // just get last element with this tag
            element = tagElements[tagElements.length - 1];
        }

        // if closing tag was not found in text
        if (tagPosition == 0) {
            // just append remaining text and exit
            element.innerHTML += text.substr(currTextPosition);
            break;
        }

        // append needed part of text to tag element content
        var symbolsCount = tagPosition - currTextPosition;
        element.innerHTML += text.substr(currTextPosition, symbolsCount);
        currTextPosition += symbolsCount;
        tagsElementMap.set(tagName, element);
    }
}

/*
Find first closed tag in text, which:
    1. was not opened in text
    2. which position > lastInsertPosition

lastInsertPosition = 0
bla</div><div>blabla</div></div>blablabla
   ^^^^^^
   needed tag

lastInsertPosition = 3
bla</div><div>blabla</div></div>blablabla
                          ^^^^^^
                          needed tag
*/
function findClosedTagPosition(text, tagName, lastInsertPosition) {
    var regexp = new RegExp("<\/" + tagName + ">|<" + tagName + ">", "g"); // opened or closed tag
    var tagPosition = 0;
    var tagOpenCloseCounter = 0; // to find first closed, but not opened tag
    while (true) {
        var found = regexp.exec(text);
        if (found === null) { // end of text
            break;
        }
        if (regexp.lastIndex <= lastInsertPosition) {
            continue;
        }

        if (found[0].includes("/")) {
            tagOpenCloseCounter -= 1; // closing tag found
        } else {
            tagOpenCloseCounter += 1; // opening tag found
        }

        if (tagOpenCloseCounter < 0) { // closing tags quantity is bigger than opening tags quantity
            tagPosition = regexp.lastIndex;
            break;
        }
    }

    return tagPosition;
}
