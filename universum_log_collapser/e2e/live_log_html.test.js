const utils = require("./utils");

beforeAll(async() => {
    await utils.openPage("generated.html");
    const expFailedStepsCount = 2; // depends on Universum test configuration
    await utils.waitForHandledResults(expFailedStepsCount);
});

test('failed steps class changed', async() => {
    await utils.checkFailedStepsHandled();
});

test("failed steps labels colored", async() => {
    let labelColors = await utils.getLabelsColors();
    expect(labelColors).toHaveLength(16);
    await utils.checkRedLabels(labelColors, [6, 8, 9, 11])
});

test("steps labels have no spans", async() => {
    let spanColors = await utils.getLabelSpansColors();
    expect(spanColors).toHaveLength(0);
});

test("failed steps expanded", async() => {
    let labelsChecked = await utils.getLabelsCheckedState();
    expect(labelsChecked).toHaveLength(16);
    utils.checkCheckedLabels(labelsChecked, [6, 8, 9, 11])
});
