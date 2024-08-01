import { Request, Response } from "express";
import Product from "../models/Product";
import Review from "../models/Review";

export const getProductByName = async (req: Request, res: Response) => {
  try {
    const productName = req.body.productName;
    const product = await Product.findOne(
      {
        name: productName,
        brand: { $exists: true },
      },
      {
        _id: 1,
        name: 1, // 상품명
        platform: 1, // 판매채널
        brand: 1, // 브랜드
        price: 1, // 가격
        reviewCount: 1, // 리뷰 수
        averageRating: 1, // 평균 별점
        breadcrumbs: 1, // 카테고리 경로
        images: 1, // 상품 이미지 URL 목록
      }
    );
    console.log("🚀 ~ getProductByName ~ product:", product);

    if (!product) {
      return res.status(404).json({ message: "Product not found" });
    }

    const result = {
      _id: product._id,
      name: product.name,
      platform: product.platform,
      brand: product.brand,
      price: product.price,
      reviewCount: product.reviewCount,
      averageRating: product.averageRating,
      breadCrumb: product.breadcrumbs,
      images: product.images,
    };

    res.json(result);
  } catch (error) {
    const err = error as Error;
    res.status(500).json({ message: err.message });
  }
};

export const getReviewsByProductName = async (req: Request, res: Response) => {
  try {
    const productName = req.params.productName;

    const reviews = await Review.aggregate([
      {
        $lookup: {
          from: "products", // products 컬렉션과 조인
          localField: "productId",
          foreignField: "_id",
          as: "product",
        },
      },
      { $unwind: "$product" }, // 배열을 개별 문서로 펼침
      { $match: { "product.name": productName } }, // 제품 이름으로 필터링
      {
        $project: {
          reviewId: "$_id",
          username: "$author.username",
          rating: "$rating",
          content: "$content",
          createdAt: "$createdAt",
          platform: "$platform",
          productName: "$product.name",
          productAverageRating: "$product.averageRating",
          productReviewCount: "$product.reviewCount",
        },
      },
    ]);

    if (reviews.length === 0) {
      return res
        .status(404)
        .json({ message: "No reviews found for the product name" });
    }

    res.json(reviews);
  } catch (error) {
    const err = error as Error;
    res.status(500).json({ message: err.message });
  }
};

// 워드 클라우드 데이터 생성 함수
// 워드 클라우드 데이터 생성 함수
export const generateWordCloudData = async (req: Request, res: Response) => {
  try {
    const productId = req.params.productId;
    const batchSize = 1000; // 한 번에 처리할 리뷰 수

    // Define the type for the word frequency object
    const wordFreq: { [key: string]: number } = {};

    // 리뷰 데이터를 스트리밍으로 배치 처리
    let skip = 0;
    let reviewsBatch;

    do {
      reviewsBatch = await Review.find({ productId })
        .skip(skip)
        .limit(batchSize)
        .exec();
      reviewsBatch.forEach((review) => {
        const text = review.content;
        if (text) {
          text.split(/\s+/).forEach((word) => {
            word = word.toLowerCase().replace(/[^\w\s]/gi, ""); // Remove punctuation
            if (!wordFreq[word]) wordFreq[word] = 0;
            wordFreq[word]++;
          });
        }
      });
      skip += batchSize;
    } while (reviewsBatch.length === batchSize);

    const wordFreqArray = Object.keys(wordFreq).map((word) => ({
      text: word,
      value: wordFreq[word],
    }));

    res.json(wordFreqArray);
  } catch (error) {
    res.status(500).json({ message: (error as Error).message });
  }
};
