// Setup testów Vitest: rejestruje matchery jest-dom (np. toBeInTheDocument)
// oraz sprząta DOM po każdym teście, aby izolować renderowania RTL.
import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});
