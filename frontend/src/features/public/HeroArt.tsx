/** Decorative fruit-popsicle composition for the public hero. Not a product photograph. */
export function HeroArt() {
  return (
    <div className="relative mx-auto aspect-square w-full max-w-[420px]" aria-hidden>
      <div className="absolute inset-6 rounded-full bg-[#E6F4EC]" />
      <div className="absolute left-[18%] top-[12%] h-[58%] w-[22%] rotate-[-18deg] rounded-full bg-gradient-to-b from-[#F4C430] to-[#E8621A] shadow-lg" />
      <div className="absolute left-[40%] top-[6%] h-[64%] w-[24%] rotate-[6deg] rounded-full bg-gradient-to-b from-[#F9A8D4] to-[#EC4899] shadow-xl" />
      <div className="absolute right-[16%] top-[16%] h-[56%] w-[22%] rotate-[16deg] rounded-full bg-gradient-to-b from-[#86EFAC] to-[#1A7A4A] shadow-lg" />
      <div className="absolute bottom-[14%] left-[26%] h-[22%] w-[8%] rounded-b-md bg-[#E8D5B5]" />
      <div className="absolute bottom-[10%] left-[48%] h-[24%] w-[9%] rounded-b-md bg-[#E8D5B5]" />
      <div className="absolute bottom-[16%] right-[26%] h-[20%] w-[8%] rounded-b-md bg-[#E8D5B5]" />
      <div className="absolute left-[12%] top-[48%] h-16 w-16 rounded-full bg-[#FDE68A]/80 blur-[2px]" />
      <div className="absolute right-[8%] top-[36%] h-12 w-12 rounded-full bg-[#BBF7D0]/90" />
    </div>
  );
}
