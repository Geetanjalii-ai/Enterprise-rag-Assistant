import React from "react";

interface AvatarProps {
  name: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export const Avatar: React.FC<AvatarProps> = ({ name, size = "md", className = "" }) => {
  const initials = name
    .split(" ")
    .map((n) => n[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase() || "U";

  const sizeClasses = {
    sm: "w-7 h-7 text-xs",
    md: "w-9 h-9 text-sm",
    lg: "w-11 h-11 text-base",
  };

  return (
    <div
      className={`rounded-full bg-lavender text-lavender-text flex items-center justify-center font-medium select-none flex-shrink-0 ${sizeClasses[size]} ${className}`}
    >
      {initials}
    </div>
  );
};
