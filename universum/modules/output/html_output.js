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
    if (parent.tagName != "PRE") {
        colorLblsAscendant(parent.previousSibling);
    }
}

function colorFailedSections() {
    var results = document.getElementsByClassName("failedStatus");
    for (var i = 0; i < results.length; i++) {
        colorLblsAscendant(results[i].parentNode.previousSibling);
    }
}


colorFailedSections();
