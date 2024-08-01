import mongoose, { Schema, Document } from "mongoose";

interface IAuthor {
  id?: string;
  username: string;
  avatar?: string;
}

interface IEvaluation {
  name: string;
  value: string;
}

interface IReview extends Document {
  _id: string;
  author: IAuthor;
  content: string;
  context: any;
  createdAt: Date;
  updatedAt?: Date;
  platform: string;
  productId: string;
  rating: number;
  likeCount?: number;
  tags: string[];
  evaluations?: IEvaluation[];
  images: string[];
  sentiment?: string;
}

const DEFAULT_AVATAR_URL = "https://example.com/default-avatar.png"; // 기본 아바타 URL

const authorSchema = new Schema(
  {
    id: { type: String, required: false },
    username: { type: String, required: true },
    avatar: { type: String, required: false, default: DEFAULT_AVATAR_URL },
  },
  { _id: false }
);

const evaluationSchema = new Schema(
  {
    name: { type: String, required: true },
    value: { type: String, required: true },
  },
  { _id: false }
);

const reviewSchema: Schema = new Schema(
  {
    _id: { type: String, required: true },
    author: { type: authorSchema, required: true },
    content: { type: String, required: true },
    context: { type: Schema.Types.Mixed, required: false },
    createdAt: { type: Date, required: true },
    updatedAt: { type: Date, required: false },
    platform: { type: String, required: true },
    productId: { type: String, required: true },
    rating: { type: Number, required: true },
    likeCount: { type: Number, required: false },
    tags: [{ type: String, required: true }],
    evaluations: { type: [evaluationSchema], required: false },
    images: [{ type: String, required: true }],
    sentiment: { type: String, required: false, default: "positive" },
  },
  {
    strict: true,
    timestamps: { createdAt: "createdAt", updatedAt: "updatedAt" },
  }
);

// 기본 인덱스 추가
reviewSchema.index({ productId: 1 });
reviewSchema.index({ createdAt: -1 });
reviewSchema.index({ platform: 1 });
reviewSchema.index({ rating: 1 });
reviewSchema.index({ content: "text" }); // 텍스트 검색을 위한 인덱스
reviewSchema.index({ "author.username": 1 }); // 작성자 이름에 대한 인덱스

const Review = mongoose.model<IReview>("Review", reviewSchema, "Review");

export default Review;
