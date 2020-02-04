const utils = require("./utils");

beforeAll(async() => {
    await utils.openPage("test.html");
    const expFailedStepsCount = 2; // depends on test HTML content
    await utils.waitForHandledResults(expFailedStepsCount);
});

test('failed steps class changed', async() => {
    await utils.checkFailedStepsHandled();
});

test("failed steps labels colored", async() => {
    let labelColors = await utils.getLabelsColors();
    expect(labelColors).toHaveLength(5);
    await utils.checkRedLabels(labelColors, [1, 2, 4])
});

test("failed steps names colored", async() => {
    let spanColors = await utils.getLabelSpansColors();
    expect(spanColors).toHaveLength(4);
    await utils.checkRedLabels(spanColors, [1, 3]);
});

test("failed steps expanded", async() => {
    let labelsChecked = await utils.getLabelsCheckedState();
    expect(labelsChecked).toHaveLength(5);
    utils.checkCheckedLabels(labelsChecked, [1, 2, 4])
});

test("pipeline issue fixed", async() => {
    let pipelineElementText = await page.$eval(".pipeline-node-7", e => e.innerHTML);
    expect(pipelineElementText).toHaveLength(0);
});

