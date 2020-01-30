beforeAll(async () => {
    const path = require('path');
    const currDir = path.dirname(module.filename);
    await page.goto('file://' + currDir + '/test.html');
    await waitForHandledResults(2);
});


test('failed steps class changed', async () => {
    const unhandledElements = await page.$$(".failed_result");
    expect(unhandledElements).toHaveLength(0);
});


test("failed steps labels colored", async() => {
    let labelColors = await page.$$eval(".sectionLbl", labels => {
        let result = [];
        for (let i = 0; i < labels.length; i++) {
            result.push(labels[i].style.color);
        }
        return result;
    });
    
    expect(labelColors).toHaveLength(5);
    expect(labelColors[0]).not.toBe("red");
    expect(labelColors[1]).toBe("red");
    expect(labelColors[2]).toBe("red");
    expect(labelColors[3]).not.toBe("red");
    expect(labelColors[4]).toBe("red");
});


test("failed steps names colored", async() => {
    let spanColors = await page.$$eval(".sectionLbl", labels => {
        let result = [];
        for (let i = 0; i < labels.length; i++) {
            let innerSpan = labels[i].querySelector("span");
            if (innerSpan != null) {
                result.push(innerSpan.style.color);
            }
        }
        return result;
    })

    expect(spanColors).toHaveLength(4);
    expect(spanColors[0]).not.toBe("red");
    expect(spanColors[1]).toBe("red");
    expect(spanColors[2]).not.toBe("red");
    expect(spanColors[3]).toBe("red");
});


test("failed steps expanded", async() => {
    let labelsChecked = await page.$$eval(".sectionLbl", labels => {
        let result = [];
        for (let i = 0; i < labels.length; i++) {
            result.push(labels[i].parentElement.previousSibling.checked);
        }
        return result;
    })

    expect(labelsChecked).toHaveLength(5);
    expect(labelsChecked[0]).toBe(false);
    expect(labelsChecked[1]).toBe(true);
    expect(labelsChecked[2]).toBe(true);
    expect(labelsChecked[3]).toBe(false);
    expect(labelsChecked[4]).toBe(true);
});


test("pipeline issue fixed", async() => {
    let pipelineElementText = await page.$eval(".pipeline-node-7", e => e.innerHTML);
    expect(pipelineElementText).toHaveLength(0);
});


async function waitForHandledResults(count) {
    const maxWait = 1000;
    let currWait = 0;
    const sleepTime = 250;
    while (true) {
        const handledElements = await page.$$(".failed_result_handled");
        if (handledElements.length == count) {
            break;
        }
        await new Promise(r => setTimeout(r, sleepTime));
        currWait += sleepTime;
        if (currWait >= maxWait) {
            throw new Error(count + " .failed_result_handled elements don't appear after 1 second");
        }
    }
}
