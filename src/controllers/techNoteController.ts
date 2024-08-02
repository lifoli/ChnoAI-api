import { Request, Response } from "express";
import express from "express";
import supabase from "../models/db";
import bodyParser from "body-parser";
// import { NotionAPI } from "notion-client";

import cors from "cors";
import path from "path";
import { fileURLToPath } from "url";

// export const getTechNoteNotionById = async (req: Request, res: Response) => {
//   try {
//     const notion = new NotionAPI();
//     const techNoteId = req.params.techNoteId;
//     const recordMap = await notion.getPage(techNoteId);
//     res.json(recordMap);

//     // if (!techNote) {
//     //   return res.status(404).json({ message: "TechNote not found" });
//     // }
//     // res.json(techNote);
//   } catch (error) {
//     const err = error as Error;
//     res.status(500).json({ message: err.message });
//   }
// };

exports.test = (req: Request, res: Response) => {
  console.log("test");
  return res.status(200).send({ message: "Product not found" });
};

exports.gettechNoteListByUserId = async (req: Request, res: Response) => {
  const userId = req.params.userId;
  // tech_notes 테이블과 conversation 테이블을 조인해서 user_id로 필터링

  const { data, error } = await supabase
    .from("tech_notes")
    .select("*, conversations!inner(user_id)")
    .eq("conversations.user_id", userId);

  if (error) {
    console.error("Error fetching tech notes:", error);
    return [];
  }

  return res.status(200).send(data);
};
