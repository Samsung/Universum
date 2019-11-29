describe('e2e tests', () => {
    beforeAll(async () => {
        const path = require('path')
        const currDir = path.dirname(module.filename);
        await page.goto('file://' + currDir + '/test.html');
    });
  
    it('"failed_result" class should be changed to "failed_result_handled"', async () => {
        const handledElement = await page.waitForSelector(".failed_result_handled");
        expect(handledElement).not.toBe(null);
        const unhandledElement = await page.$(".failed_result");
        expect(unhandledElement).toBe(null);
    });
});
