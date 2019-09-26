var coloringTimeoutMilliSeconds = 250;
var timerId = setInterval(colorFailedSections, coloringTimeoutMilliSeconds);

function colorLblsAscendant(el) {
    var sectionLbl = el.getElementsByClassName("sectionLbl")[0];
    sectionLbl.style.color = "red";
    sectionLbl.getElementsByTagName("span")[0].style.cssText = "color:red !important";
    var parent = el.parentNode;
    if (parent.className != "console-output") {
        colorLblsAscendant(parent.previousSibling);
    }
}

function colorFailedSections() {
    var results = document.getElementsByClassName("failed_result");
    for (var i = 0; i < results.length; i++) {
        var element = results[i];
        colorLblsAscendant(element.parentNode.previousSibling);
        element.className = "failed_result_handled";
    }
}

function finishColoring() {
    clearInterval(timerId);

    /*
     If universum step execution takes long time, Jenkins closes current <pre> and opens new one, which broke
     sections displaying. This is fixed by page refresh.
     */
    var preElement = document.getElementsByClassName("console-output")[0];
    if (preElement.getElementsByTagName("pre").length > 0) {
        document.location.reload();
    }

    setTimeout(colorFailedSections, coloringTimeoutMilliSeconds);
}
