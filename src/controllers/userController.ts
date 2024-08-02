import { Request, Response } from "express";
import supabase from "../models/db";
import { User } from "../types/User";

exports.getInfoByUserId = async (req: Request, res: Response) => {
  const userId = req.params.userId;
  console.log("🚀 ~ exports.getInfoByUserId= ~ userId:", userId);
  const { data, error } = await supabase
    .from("users")
    .select(`*`)
    .eq("id", userId);
  // data가 빈 리스트라면 404
  if (data?.length === 0) {
    return res.status(404).json({ message: "User not found" });
  }
  const user = data?.[0];

  return res.status(200).send(data);
};

exports.createUser = async (req: Request, res: Response) => {
  const { user } = req.body;
  const { nbf, jti, exp, iat, ...newUser } = user;

  // // 예제 사용법
  // const newUser: Omit<User, "id"> = { ...user };

  const { data, error } = await supabase
    .from("users")
    .insert([newUser])
    .select("*")
    .single();
  if (error) {
    return res.status(500).json({ message: error.message });
  }
  return res.status(201).json(data);
};
