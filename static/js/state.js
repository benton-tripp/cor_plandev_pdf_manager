// state.js

// Unified state object
export const state = {
    pdfDoc: null
};

// General setter for state properties
export function setState(key, value) {
    if (key in state) {
        state[key] = value;
    } else {
        throw new Error(`State key '${key}' does not exist.`);
    }
}
