/** The attributes for the one panel that follows a tablist built with <TabList idBase="x">. */
export function panelProps(idBase: string, selected: string) {
  return { id: `${idBase}-panel`, role: "tabpanel" as const, "aria-labelledby": `${idBase}-tab-${selected}`, tabIndex: 0 };
}
