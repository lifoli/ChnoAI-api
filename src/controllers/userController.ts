import { Request, Response } from "express";
import supabase from "../models/db";
import { User } from "../types/User";

exports.getInfoByUserId = async (req: Request, res: Response) => {
  const userId = req.params.userId;

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

  // 유저가 이미 존재하는지 확인
  const { data: existingUser, error: selectError } = await supabase
    .from("users")
    .select("*")
    .eq("email", newUser.email)
    .single();

  if (selectError && selectError.code !== "PGRST116") {
    // 다른 에러 발생 시 처리
    return res.status(500).json({ message: selectError.message });
  }

  if (existingUser) {
    // 유저가 이미 존재할 경우 해당 유저의 데이터를 반환
    return res.status(200).json(existingUser);
  }

  // 유저가 존재하지 않으면 새 유저 생성
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
