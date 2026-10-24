import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import { App } from "../App";

export function renderAt(url: string) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <App />
    </MemoryRouter>,
  );
}
