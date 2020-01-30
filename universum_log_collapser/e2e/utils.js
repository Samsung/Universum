module.exports = {
    waitForHandledResults: async function(count) {
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
}
