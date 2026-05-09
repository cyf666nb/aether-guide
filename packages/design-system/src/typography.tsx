import type { HTMLAttributes, ReactNode } from "react";

type TextProps = HTMLAttributes<HTMLElement> & {
  as?: "p" | "span" | "div";
  children: ReactNode;
};

type HeadingProps = HTMLAttributes<HTMLHeadingElement> & {
  level?: 1 | 2 | 3;
  children: ReactNode;
};

export function Display({ children, className = "", ...props }: TextProps) {
  return (
    <p className={`type-display ${className}`} {...props}>
      {children}
    </p>
  );
}

export function Heading({ level = 2, children, className = "", ...props }: HeadingProps) {
  const Tag = `h${level}` as const;
  return (
    <Tag className={`type-heading type-heading-${level} ${className}`} {...props}>
      {children}
    </Tag>
  );
}

export function Body({ as: Tag = "p", children, className = "", ...props }: TextProps) {
  return (
    <Tag className={`type-body ${className}`} {...props}>
      {children}
    </Tag>
  );
}

export function Mono({ as: Tag = "span", children, className = "", ...props }: TextProps) {
  return (
    <Tag className={`type-mono ${className}`} {...props}>
      {children}
    </Tag>
  );
}

