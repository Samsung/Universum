module.exports = {
    openPage: async function(fileName) {
        const path = require('path');
        const currDir = path.dirname(module.filename);
        await page.goto('file://' + currDir + '/' + fileName);
    },

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
    },

    checkFailedStepsHandled: async function() {
        const unhandledElements = await page.$$(".failed_result");
        expect(unhandledElements).toHaveLength(0);
    },

    getLabelsColors: async function() {
        return await page.$$eval(".sectionLbl", labels => {
            let result = [];
            for (let i = 0; i < labels.length; i++) {
                result.push(labels[i].style.color);
            }
            return result;
        });
    },

    checkRedLabels: async function(labelsColors, indexes) {
        let maxIndex = Math.max.apply(null, indexes);
        expect(maxIndex).toBeLessThan(labelsColors.length);

        for (let i = 0; i < labelsColors.length; i++) {
            let color = labelsColors[i]; 
            if (indexes.includes(i)) {
                expect(color).toBe("red");
            } else {
                expect(color).not.toBe("red");
            }
        }
    },

    getLabelSpansColors: async function() {
        return await page.$$eval(".sectionLbl", labels => {
            let result = [];
            for (let i = 0; i < labels.length; i++) {
                let innerSpan = labels[i].querySelector("span");
                if (innerSpan != null) {
                    result.push(innerSpan.style.color);
                }
            }
            return result;
        });
    },

    getLabelsCheckedState: async function() {
        return await page.$$eval(".sectionLbl", labels => {
            let result = [];
            for (let i = 0; i < labels.length; i++) {
                result.push(labels[i].parentElement.previousSibling.checked);
            }
            return result;
        });
    },

    checkCheckedLabels: async function(labelsChecked, indexes) {
        let maxIndex = Math.max.apply(null, indexes);
        expect(maxIndex).toBeLessThan(labelsChecked.length);

        for (let i = 0; i < labelsChecked.length; i++) {
            let state = labelsChecked[i]; 
            expect(state).toBe(indexes.includes(i));
        }
    }
}
