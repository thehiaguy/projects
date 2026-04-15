"use client";

export default function StartStopCallButton({ isLive, disabled, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`rounded-full px-5 py-3 text-sm font-semibold transition ${
        disabled
          ? "cursor-not-allowed bg-slate-200 text-slate-400"
          : isLive
            ? "bg-slate-900 text-white hover:bg-slate-800"
            : "bg-[#f4c95d] text-slate-950 hover:bg-[#efbe43]"
      }`}
    >
      {isLive ? "Stop session" : "Start session"}
    </button>
  );
}
