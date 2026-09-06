import "@testing-library/jest-dom/vitest";

// jsdom doesn't implement layout, so Element.scrollIntoView is undefined —
// App.tsx calls it to keep the transcript pinned to the latest event. Stub
// it as a no-op rather than special-casing the app code for the test
// environment.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}
