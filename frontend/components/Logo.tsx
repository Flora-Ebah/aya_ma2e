import Image from "next/image";

export default function Logo({ size = 36, className = "" }: { size?: number; className?: string }) {
  return (
    <Image
      src="/logo.png"
      alt="MA2E"
      width={size}
      height={size}
      priority
      className={className}
    />
  );
}
