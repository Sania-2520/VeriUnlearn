import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import * as React from "react";

jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

jest.mock("next/link", () => {
  const MockLink = React.forwardRef<HTMLAnchorElement, React.AnchorHTMLAttributes<HTMLAnchorElement>>(
    ({ children, href, ...props }, ref) => (
      <a ref={ref} href={href as string} {...props}>
        {children}
      </a>
    )
  );
  MockLink.displayName = "MockLink";
  return MockLink;
});

jest.mock("@/lib/store/auth-store", () => ({
  useAuthStore: () => ({
    isAuthenticated: false,
    isLoading: false,
    loadUser: jest.fn(),
  }),
}));

import Home from "@/app/page";

describe("Home page smoke tests", () => {
  it("renders without crashing", () => {
    render(<Home />);
  });

  it("displays the welcome heading", () => {
    render(<Home />);
    expect(
      screen.getByRole("heading", { name: /welcome to veriunlearn/i })
    ).toBeInTheDocument();
  });

  it("renders the prompt input", () => {
    render(<Home />);
    expect(
      screen.getByPlaceholderText(/ask anything about machine unlearning/i)
    ).toBeInTheDocument();
  });

  it("renders navigation links", () => {
    render(<Home />);
    expect(screen.getByText("Log In")).toBeInTheDocument();
    expect(screen.getByText("Sign Up")).toBeInTheDocument();
  });

  it("renders suggestion cards", () => {
    render(<Home />);
    expect(
      screen.getByText(/initiate data deletion request/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/verify cryptographic proof/i)
    ).toBeInTheDocument();
  });

  it("renders the footer", () => {
    render(<Home />);
    expect(screen.getByText(/gdpr compliant/i)).toBeInTheDocument();
    expect(screen.getByText(/© 2026 veriunlearn/i)).toBeInTheDocument();
  });
});
