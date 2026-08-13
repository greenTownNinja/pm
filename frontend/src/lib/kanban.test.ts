import { moveCard, resolveDrop, type Column } from "@/lib/kanban";

const baseColumns: Column[] = [
  { id: "col-a", title: "A", cardIds: ["card-1", "card-2"] },
  { id: "col-b", title: "B", cardIds: ["card-3"] },
];

describe("moveCard", () => {

  it("reorders cards in the same column", () => {
    const result = moveCard(baseColumns, "card-2", "card-1");
    expect(result[0].cardIds).toEqual(["card-2", "card-1"]);
  });

  it("moves cards to another column", () => {
    const result = moveCard(baseColumns, "card-2", "card-3");
    expect(result[0].cardIds).toEqual(["card-1"]);
    expect(result[1].cardIds).toEqual(["card-2", "card-3"]);
  });

  it("drops cards to the end of a column", () => {
    const result = moveCard(baseColumns, "card-1", "col-b");
    expect(result[0].cardIds).toEqual(["card-2"]);
    expect(result[1].cardIds).toEqual(["card-3", "card-1"]);
  });
});

describe("resolveDrop", () => {
  it("reads the index from the pre-move column when reordering", () => {
    expect(resolveDrop(baseColumns, "card-1", "card-2")).toEqual({
      columnId: "col-a",
      position: 1,
    });
  });

  it("targets the index of the card being dropped on", () => {
    expect(resolveDrop(baseColumns, "card-1", "card-3")).toEqual({
      columnId: "col-b",
      position: 0,
    });
  });

  it("appends when dropped on a column", () => {
    expect(resolveDrop(baseColumns, "card-1", "col-b")).toEqual({
      columnId: "col-b",
      position: 1,
    });
    // Its own column, so the card no longer counts towards the end.
    expect(resolveDrop(baseColumns, "card-1", "col-a")).toEqual({
      columnId: "col-a",
      position: 1,
    });
  });

  it("returns null for ids that do not resolve", () => {
    expect(resolveDrop(baseColumns, "card-1", "nope")).toBeNull();
    expect(resolveDrop(baseColumns, "nope", "card-1")).toBeNull();
  });
});
