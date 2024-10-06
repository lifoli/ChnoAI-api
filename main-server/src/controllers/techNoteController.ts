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

exports.test = async (req: Request, res: Response) => {
  console.log("test");

  await sendSlackNotification("test");

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

async function sendSlackNotification(message: string) {
  const webhookUrl =
    "https://hooks.slack.com/services/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"; // 위에서 생성한 Webhook URL을 여기에 삽입합니다.

  const payload = {
    text: message, // 슬랙 채널에 보낼 메시지
  };

  try {
    await axios.post(webhookUrl, payload); // 슬랙으로 HTTP POST 요청을 보냅니다.
    console.log("슬랙 알림 전송 성공!");
  } catch (error) {
    console.error("슬랙 알림 전송 실패:", error);
  }
}

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
      .get(`http://${aiServerContainerName}:4000/process-url?url=${url}`)
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

    // init slack notification
    await sendSlackNotification(`
      새로운 기술 노트 요청 init
      대화 id: ${conversationData.id}
    `);

    return res.status(201).json({ techNoteData });
  } catch (error) {
    console.error("Unexpected error:", error);
    return res.status(500).json({ message: "An unexpected error occurred" });
  }
};

exports.createNotionPage = async (req: Request, res: Response) => {
  const { conversation_id } = req.params;
  console.log(conversation_id);

  try {
    // 한국을 기준으로 현재 시각으로부터 6시간뒤의 시간을 deadline으로 string형태로 전달
    const deadline = new Date();
    deadline.setHours(deadline.getHours() + 6);
    const deadlineString = deadline.toLocaleString("ko-KR", {
      timeZone: "Asia/Seoul",
    });

    const { data: conversation, error: conversationError } = await supabase
      .from("conversations")
      .select()
      .eq("id", conversation_id)
      .single();

    const { data: user, error: userError } = await supabase
      .from("users")
      .select()
      .eq("id", conversation?.user_id)
      .single();

    const { data: techNote, error: techNoteError } = await supabase
      .from("tech_notes")
      .select()
      .eq("conversation_id", conversation_id)
      .single();

    const aiServerContainerName: string =
      process.env.NODE_ENV === "development" ? "ai-server-dev" : "ai-server";

    const result = await axios
      .post(`http://${aiServerContainerName}:4000/generate-blog2`, {
        conversation_id: conversation_id,
      })
      .then((response) => {
        return response.data;
      })
      .catch((error) => {
        console.error("Error fetching Notion data:", error);
        return null;
      });

    //supabase에서 tech_notes테이블의 notion_link항목을 result.notion_page_public_url로 업데이트
    const { data: techNoteUpdateData, error: techNoteUpdateError } =
      await supabase
        .from("tech_notes")
        .update({ notion_link: result.notion_page_public_url })
        .eq("id", techNote?.id)
        .single();

    // 담당자설정, 생성된 technote id가 짝수일시 "이흥규", 홀수일시 "최영섭"으로 설정
    const assignee = techNote?.id % 2 === 0 ? "이흥규" : "최영섭";

    // 슬랙 알림 전송
    await sendSlackNotification(`
      새로운 기술 노트 요청.
      대화 id: ${conversation_id}
      유저명: ${user.name}
      유저 이메일: ${user.email}
      제목: ${techNote?.title}
      대화창 링크: ${conversation?.link}
      notion_page_id: ${result.notion_page_id}
      notion_page_url: ${result.notion_page_url}
      notion_page_public_url: ${result.notion_page_public_url}
      마감기한: ${deadlineString}
      담당자: ${assignee}
    `);
    console.log("작업끝");
    return res.status(201).json({});
  } catch {
    console.log("슬랙 알림 전송 실패");
  }
};
