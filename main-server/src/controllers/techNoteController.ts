import { Request, Response } from "express";
import supabase from "../models/db";
import axios from "axios";

exports.getTechNoteNotionByPageId = async (req: Request, res: Response) => {
  try {
    const notionPageId: string = req.params.notionPageId;
    const notionServerContainerName: string =
      process.env.NODE_ENV === "development"
        ? "notion-server-dev"
        : "notion-server";
    const recordMap = await axios
      .get(`http://${notionServerContainerName}:8000/notion/${notionPageId}`)
      .then((response) => {
        return response.data;
      })
      .catch((error) => {
        console.error("Error fetching Notion data:", error);
        return null;
      });
    res.status(200).json({ notionPageData: recordMap });
  } catch (error) {
    const err = error as Error;
    res.status(500).json({ message: err.message });
  }
};

exports.test = (req: Request, res: Response) => {
  console.log("test");
  return res.status(200).send({ message: "Product not found" });
};

exports.createTechNoteFromExtension = async (req: Request, res: Response) => {
  const { user_id, title, data } = req.body;

  if (!user_id || !data) {
    return res
      .status(400)
      .json({ message: "Missing required fields: user_id or raw_content" });
  }

  try {
    // conversations 테이블에 데이터 추가
    const { data: conversationData, error: conversationError } = await supabase
      .from("conversations")
      .insert([
        {
          user_id,
          source: "chrome_extension",
        },
      ])
      .select("*")
      .single();

    if (conversationError) {
      console.error("Error inserting conversation:", conversationError);
      return res.status(500).json({ message: "Error inserting conversation" });
    }

    const messages = data.flatMap(
      (
        { question, answer }: { question: string; answer: string },
        index: number
      ) => [
        {
          message_type: "question",
          message_content: question,
          conversation_id: conversationData.id,
          sequence_number: index * 2 + 1,
        },
        {
          message_type: "answer",
          message_content: answer,
          conversation_id: conversationData.id,
          sequence_number: index * 2 + 2,
        },
      ]
    );

    // tech_notes 테이블에 데이터 추가
    const { data: techNoteData, error: techNoteError } = await supabase
      .from("tech_notes")
      .insert([
        {
          conversation_id: conversationData.id,
          title: "Preparing the notes.",
          note_content: "",
          is_completed: false,
        },
      ])
      .select("*")
      .single();

    if (techNoteError) {
      console.error("Error inserting tech note:", techNoteError);
      return res.status(500).json({ message: "Error inserting tech note" });
    }

    // messages 테이블에 데이터 추가
    const { data: messagesData, error: messagesError } = await supabase
      .from("messages")
      .insert(messages)
      .select("*");

    if (messagesError) {
      console.error("Error inserting messages:", messagesError);
      return res.status(500).json({ message: "Error inserting messages" });
    }

    return res.status(201).json({ techNoteData });
  } catch (error) {
    console.error("Unexpected error:", error);
    return res.status(500).json({ message: "An unexpected error occurred" });
  }
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

// service함수로 이전

exports.createTechNoteFromLink = async (req: Request, res: Response) => {
  const { user_id, url } = req.body;

  if (!user_id || !url) {
    return res
      .status(400)
      .json({ message: "Missing required fields: user_id or url" });
  }
  console.log("작업 시작");
  try {
    // // Bottleneck 리미터를 사용하여 runHeadlessBrowser 함수를 호출합니다.
    // const { chatUrl, chatRoomTitle, data } = await limiter.schedule(() =>
    //   runHeadlessBrowser(url)
    // );

    // conversations 테이블에 데이터 추가
    const { data: conversationData, error: conversationError } = await supabase
      .from("conversations")
      .insert([
        {
          user_id,
          source: "direct_link",
          link: url,
        },
      ])
      .select("*")
      .single();

    // 데이터가 없을 경우 에러 처리
    if (conversationError) {
      console.error("Error inserting conversation:", conversationError);
      return res.status(500).json({ message: "Error inserting conversation" });
    }
    const aiServerContainerName: string =
      process.env.NODE_ENV === "development" ? "ai-server-dev" : "ai-server";
    const conversation: {
      data: any[];
      chatUrl: string;
      chatRoomTitle: string;
    } | null = await axios
      .get(`http://${aiServerContainerName}:3000/process-url?url=${url}`)
      .then((response) => {
        return {
          data: response.data.data,
          chatUrl: response.data.chatUrl,
          chatRoomTitle: response.data.chatRoomTitle,
        };
      })
      .catch((error) => {
        console.error("Error fetching Notion data:", error);
        return null;
      });

    console.log(
      "🚀 ~ exports.createTechNoteFromLink= ~ conversation:",
      conversation
    );

    const messages = conversation?.data.flatMap(
      ({ question, answer }, index) => [
        {
          message_type: "question",
          message_content: question,
          conversation_id: conversationData.id,
          sequence_number: index * 2 + 1,
        },
        {
          message_type: "answer",
          message_content: answer,
          conversation_id: conversationData.id,
          sequence_number: index * 2 + 2,
        },
      ]
    );

    // tech_notes 테이블에 데이터 추가
    const { data: techNoteData, error: techNoteError } = await supabase
      .from("tech_notes")
      .insert([
        {
          conversation_id: conversationData.id,
          // 현재 날짜, 시간을 기준으로 제목 생성(영어로)
          title: conversation?.chatRoomTitle,
          note_content: "",
          is_completed: false,
        },
      ])
      .select("*")
      .single();

    if (techNoteError) {
      console.error("Error inserting tech note:", techNoteError);
      return res.status(500).json({ message: "Error inserting tech note" });
    }

    // messages 테이블에 데이터 추가
    const { data: messagesData, error: messagesError } = await supabase
      .from("messages")
      .insert(messages)
      .select("*");

    if (messagesError) {
      console.error("Error inserting messages:", messagesError);
      return res.status(500).json({ message: "Error inserting messages" });
    }

    return res.status(201).json({ techNoteData });
  } catch (error) {
    console.error("Unexpected error:", error);
    return res.status(500).json({ message: "An unexpected error occurred" });
  }
};
