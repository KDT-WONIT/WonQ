const paths = {
  home: "m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1zM9 21v-7h6v7",
  box: "m12 3 9 4.5v9L12 21l-9-4.5v-9zM3 7.5l9 4.5 9-4.5M12 12v9M7.5 5.25l9 4.5",
  audit: "M9 5H6a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1h-3M9 3h6v4H9zM9 14l2 2 4-4",
  report: "M6 3h8l4 4v14H6zM14 3v5h4M9 16h6m-6-4h6",
  swap: "M3 8h17m-4-4 4 4-4 4M21 16H4m4-4-4 4 4 4",
  pin: "M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z M14 10a2 2 0 1 0-4 0 2 2 0 1 0 4 0",
  meg: "M3 10v4h4l10 4V6L7 10zm4 4 2 6h3l-2-5m10-5 2-1m-2 5 2 1",
  search: "M17 10.5a6.5 6.5 0 1 0-13 0 6.5 6.5 0 1 0 13 0Zm-1 5.5 4.5 4.5",
  bell: "M18 8a6 6 0 0 0-12 0c0 6-3 7-3 9h18c0-2-3-3-3-9m-8 12a2 2 0 0 0 4 0",
  arrow: "m9 6 6 6-6 6",
  down: "m6 9 6 6 6-6",
  close: "m6 6 12 12M18 6 6 18",
  menu: "M4 6h16M4 12h16M4 18h16",
  calendar: "M3 5h18v16H3zM3 10h18M8 3v4m8-4v4",
  warning: "M10.4 4.4 3 18a1.3 1.3 0 0 0 1.1 2h15.8a1.3 1.3 0 0 0 1.1-2L13.6 4.4a1.8 1.8 0 0 0-3.2 0Z M12 9v4m0 3v.1",
  plus: "M12 5v14m-7-7h14",
  chat: "M20 11.5a8 8 0 0 1-8 8H4l2-3a8 8 0 1 1 14-5Z M8 11.5h.1m3.9 0h.1m3.9 0h.1",
  download: "M12 3v12m-4-4 4 4 4-4M5 17v4h14v-4",
  user: "M15.5 8a3.5 3.5 0 1 0-7 0 3.5 3.5 0 1 0 7 0ZM5 21v-2a7 7 0 0 1 14 0v2",
  send: "m3 4 18 8-18 8 3-8zm3 8h15",
  truck: "M2 6h12v12H2zM14 10h4l4 4v4h-8m-9 0v2m14-2v2",
  refresh: "M20 10a8 8 0 1 0-.8 6M20 4v6h-6",
};

export type IconName = keyof typeof paths;

export function Icon({ name, className = "" }: { name: IconName; className?: string }) {
  return <svg className={`ico ${className}`} viewBox="0 0 24 24" aria-hidden="true"><path d={paths[name]} /></svg>;
}
