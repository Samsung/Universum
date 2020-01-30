const utils = require("./utils");

beforeAll(async () => {
    await utils.openPage("generated.html");
    await utils.waitForHandledResults(2);
});

test('failed steps class changed', async () => {
    await utils.checkFailedStepsHandled();
});

test("failed steps labels colored", async() => {
    let labelColors = await utils.getLabelsColors();
    expect(labelColors).toHaveLength(15);
    await utils.checkRedLabels(labelColors, [5, 7, 8, 10])
});

test("steps labels have no spans", async() => {
    let spanColors = await utils.getLabelSpansColors();
    expect(spanColors).toHaveLength(0);
});

test("failed steps expanded", async() => {
    let labelsChecked = await utils.getLabelsCheckedState();
    expect(labelsChecked).toHaveLength(15);
    utils.checkCheckedLabels(labelsChecked, [5, 7, 8, 10])
});
