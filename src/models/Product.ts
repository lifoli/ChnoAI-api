import mongoose, { Schema, Document } from "mongoose";

// 가능한 platform 값들을 Union 타입으로 정의
type PlatformType = "brand.naver.com" | "oliveyoung.co.kr";

interface IEvaluation {
  name: string;
  value: number;
}

interface IProduct extends Document {
  _id: string;
  url: string;
  context: any;
  updatedAt: Date;
  averageRating: number;
  brand: string;
  images: string[];
  name: string;
  platform: PlatformType; // Union 타입 적용
  price: number;
  reviewCount: number;
  typicalPrice: number;
  breadcrumbs: string[];
  stock?: number;
  evaluations: IEvaluation[];
}

const evaluationSchema = new Schema(
  {
    name: { type: String, required: true },
    value: { type: Number, required: true },
  },
  { _id: false }
);

const productSchema: Schema = new Schema(
  {
    _id: { type: String, required: true },
    url: { type: String, required: true },
    context: Schema.Types.Mixed,
    updatedAt: { type: Date, required: true },
    averageRating: { type: Number, required: true },
    brand: { type: String, required: true },
    images: [{ type: String, required: true }],
    name: { type: String, required: true },
    platform: {
      type: String,
      enum: ["brand.naver.com", "oliveyoung.co.kr"],
      required: true,
    }, // enum 타입으로 강제
    price: { type: Number, required: true },
    reviewCount: { type: Number, required: true },
    typicalPrice: { type: Number, required: true },
    breadcrumbs: [{ type: String, required: true }],
    stock: { type: Number, required: false },
    evaluations: [evaluationSchema],
  },
  {
    strict: true,
    timestamps: true,
  }
);

// 기본 인덱스 추가
productSchema.index({ name: 1 });
productSchema.index({ brand: 1 });
productSchema.index({ platform: 1 });
productSchema.index({ averageRating: -1 });
productSchema.index({ reviewCount: -1 });

// 인덱스 설정 (필요에 따라 추가)
// productSchema.index({ platform: 1, name: 1 });
// productSchema.index({ brand: 1 });
// productSchema.index({ price: 1 });
// productSchema.index({ averageRating: -1 });
// productSchema.index({ reviewCount: -1 });

const Product = mongoose.model<IProduct>("Product", productSchema, "Product");

export default Product;
