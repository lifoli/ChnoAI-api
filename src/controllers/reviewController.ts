import { Request, Response } from "express";
import Product from "../models/Product";
import Review from "../models/Review";
import { PipelineStage } from "mongoose";

exports.test = (req: Request, res: Response) => {
  console.log("test");
  return res.status(200).send({ message: "Product not found" });
};
// 특정 username을 가진 모든 리뷰와 해당 상품 정보를 가져오는 함수
type SortOptions = "latest" | "oldest" | "highestRating" | "lowestRating";

const getSortCondition = (sortOption: SortOptions): Record<string, 1 | -1> => {
  switch (sortOption) {
    case "latest":
      return { createdAt: -1 };
    case "oldest":
      return { createdAt: 1 };
    case "highestRating":
      return { rating: -1 };
    case "lowestRating":
      return { rating: 1 };
    default:
      return { createdAt: -1 }; // 기본값: 최신순
  }
};

// 특정 username을 가진 모든 리뷰와 해당 상품 정보를 가져오는 함수
export const getReviewsByUsername = async (req: Request, res: Response) => {
  try {
    const username = req.params.username;
    const sortOption = (req.query.sort as SortOptions) || "최신순"; // 'SortOptions' 타입으로 캐스팅

    // 기본 매치 조건
    const matchConditions: any = {
      "author.username": username,
    };

    const sortCondition = getSortCondition(sortOption);

    let reviews = await Review.aggregate([
      { $match: matchConditions },
      {
        $lookup: {
          from: "Product",
          localField: "productId",
          foreignField: "_id",
          as: "product",
        },
      },
      { $unwind: "$product" },
      { $sort: sortCondition },
    ]);

    if (reviews.length === 0) {
      return res
        .status(404)
        .json({ message: "No reviews found for the username" });
    }

    const formattedReviews = reviews.map((review) => ({
      reviewId: review._id,
      username: review.author.username,
      rating: review.rating,
      content: review.content,
      createdAt: review.createdAt,
      platform: review.platform,
      productName: review.product.name,
      productAverageRating: review.product.averageRating,
      productReviewCount: review.product.reviewCount,
    }));

    res.json(formattedReviews);
  } catch (error) {
    const err = error as Error; // 'Error' 타입으로 캐스팅
    res.status(500).json({ message: err.message });
  }
};

export const getReviewSummaryByUsername = async (
  req: Request,
  res: Response
) => {
  try {
    const username = req.params.username;

    // 기본 매치 조건
    const matchConditions: any = {
      "author.username": username,
    };

    // 리뷰 요약 정보 조회
    const reviewSummary = await Review.aggregate([
      { $match: matchConditions },
      {
        $group: {
          _id: "$author.username",
          reviewCount: { $sum: 1 },
          averageRating: { $avg: "$rating" },
          totalRecommendations: { $sum: "$recommCnt" },
        },
      },
    ]);

    if (reviewSummary.length === 0) {
      return res
        .status(404)
        .json({ message: "No reviews found for the username" });
    }

    res.json(reviewSummary[0]);
  } catch (error) {
    const err = error as Error; // 'Error' 타입으로 캐스팅
    res.status(500).json({ message: err.message });
  }
};
export const getUserActivityTrend = async (req: Request, res: Response) => {
  try {
    const username = req.params.username;

    const today = new Date();
    const monthEnds = [];
    for (let i = 0; i < 6; i++) {
      const endOfMonth = new Date(
        today.getFullYear(),
        today.getMonth() - i + 1,
        0
      );
      monthEnds.push(endOfMonth);
    }

    const reviews = await Review.aggregate([
      { $match: { "author.username": username } },
      {
        $group: {
          _id: {
            year: { $year: "$createdAt" },
            month: { $month: "$createdAt" },
          },
          count: { $sum: 1 },
        },
      },
      {
        $sort: {
          "_id.year": -1,
          "_id.month": -1,
        },
      },
    ]);

    // Initialize review counts with zero
    const reviewCounts = monthEnds.map((date) => ({
      date,
      count: 0,
    }));

    // Accumulate review counts for each month
    reviews.forEach((review) => {
      const reviewDate = new Date(review._id.year, review._id.month - 1);
      reviewCounts.forEach((reviewCount) => {
        if (reviewDate <= reviewCount.date) {
          reviewCount.count += review.count;
        }
      });
    });

    // Accumulate counts to be cumulative
    for (let i = reviewCounts.length - 1; i > 0; i--) {
      reviewCounts[i - 1].count += reviewCounts[i].count;
    }

    res.json(
      reviewCounts.map((reviewCount, index) => ({
        month: 7 - index,
        date: reviewCount.date,
        count: reviewCount.count,
      }))
    );
  } catch (error) {
    const err = error as Error;
    res.status(500).json({ message: err.message });
  }
};

export const getReviewsByProductName = async (req: Request, res: Response) => {
  try {
    const productName = req.params.productName;
    const reviews = await Review.find({ name: productName }).exec();
    res.json(reviews);
  } catch (error) {
    const err = error as Error;
    res.status(500).json({ message: err.message });
  }
};

export const getProductActivityTrend = async (req: Request, res: Response) => {
  try {
    const { productName } = req.body;

    console.log("Received productName:", productName); // 입력된 productName 확인

    // productName을 기반으로 상품 정보 조회
    const product = await Product.findOne({ name: productName }).exec();
    if (!product) {
      console.log("Product not found for productName:", productName); // 상품이 없는 경우 로그
      return res.status(404).json({ message: "Product not found" });
    }

    const productId = product._id;
    const reviewCount = product.reviewCount;

    console.log("Found productId:", productId); // 조회된 productId 확인
    console.log("Total reviewCount:", reviewCount); // 조회된 reviewCount 확인

    // 오늘 날짜를 기준으로 이전 6개월의 말일과 그 이전 1일을 계산
    const today = new Date();
    const monthEnds = [];
    for (let i = 0; i < 6; i++) {
      const endOfMonth = new Date(
        today.getFullYear(),
        today.getMonth() - i + 1,
        0
      );
      const startOfMonth = new Date(
        today.getFullYear(),
        today.getMonth() - i,
        1
      );
      monthEnds.push({ startOfMonth, endOfMonth });
      console.log(`Start of month ${i + 1}:`, startOfMonth); // 계산된 각 월의 첫 날 확인
      console.log(`End of month ${i + 1}:`, endOfMonth); // 계산된 각 월의 마지막 날 확인
    }

    // 각 월의 시작 날짜와 마지막 날짜를 기준으로 리뷰 수를 집계
    const monthlyReviewCounts = await Promise.all(
      monthEnds.map(async (month) => {
        const reviewCount = await Review.countDocuments({
          productId,
          createdAt: { $gte: month.startOfMonth, $lte: month.endOfMonth },
        }).exec();
        console.log(
          `Review count for ${month.startOfMonth} to ${month.endOfMonth}:`,
          reviewCount
        ); // 각 월의 리뷰 수 확인
        return { date: month.endOfMonth, count: reviewCount };
      })
    );

    res.json({ productId, reviewCount, monthlyReviewCounts });
  } catch (error) {
    const err = error as Error;
    console.log("Error occurred:", err.message); // 에러 메시지 로그
    res.status(500).json({ message: err.message });
  }
};

interface QueryInput {
  keywords: string[];
  platforms: string[];
  brands: string[];
  productNames: string[];
  createdDate: string;
  ratings: number[];
  sortBy: string;
  authors: string[];
  page: number;
  limit: number;
}

const getStartDate = (createdDate: string): Date | null => {
  const today = new Date();
  switch (createdDate) {
    case "24시간 이내":
      return new Date(today.getTime() - 24 * 60 * 60 * 1000);
    case "일주일 이내":
      return new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
    case "한 달 이내":
      return new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
    default:
      return null;
  }
};

// MongoDB의 $sort 스테이지에 사용될 수 있는 값들의 타입을 정의
type SortDirection = 1 | -1;
type MetaSort = { $meta: string };
type SortValue = SortDirection | MetaSort;

// getSortStage 함수의 반환 타입을 명시적으로 지정
const getSortStage = (sortBy: string): Record<string, SortDirection> => {
  switch (sortBy) {
    case "최신순":
      return { createdAt: -1 };
    case "오래된순":
      return { createdAt: 1 };
    case "평점높은순":
      return { rating: -1 };
    case "평점낮은순":
      return { rating: 1 };
    default:
      return { createdAt: -1 };
  }
};

export const searchReviews = async (req: Request, res: Response) => {
  console.log("Starting searchReviews function");
  const input: QueryInput = req.body;
  console.log("Input received:", input);

  const pipeline: PipelineStage[] = [];
  let indexHint: any = {};

  // 1. Match stage for initial filtering
  console.log("Building initial match stage");
  const matchStage: any = {};

  // 기본 필터링 조건 추가 (예: 최근 3개월 데이터만 조회)
  const threeMonthsAgo = new Date();
  threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
  matchStage.createdAt = { $gte: threeMonthsAgo };

  // Keywords (텍스트 검색 사용)
  if (input.keywords.length > 0) {
    matchStage.$text = { $search: input.keywords.join(" ") };
    console.log("Keywords filter:", matchStage.$text);
    indexHint = null;
  }

  // Platforms
  if (input.platforms.length > 0) {
    matchStage.platform = { $in: input.platforms };
    console.log("Platforms filter:", matchStage.platform);
    if (indexHint !== null && Object.keys(indexHint).length === 0)
      indexHint.platform = 1;
  }

  // Ratings
  if (input.ratings.length > 0) {
    matchStage.rating = { $in: input.ratings.map((r) => r / 5) };
    console.log("Ratings filter:", matchStage.rating);
    if (indexHint !== null && Object.keys(indexHint).length === 0)
      indexHint.rating = 1;
  }

  // Created Date
  const startDate = getStartDate(input.createdDate);
  if (startDate) {
    matchStage.createdAt = { $gte: startDate };
    console.log("Created Date filter:", matchStage.createdAt);
    if (indexHint !== null && Object.keys(indexHint).length === 0)
      indexHint.createdAt = -1;
  }

  // Authors
  if (input.authors.length > 0) {
    matchStage["author.username"] = { $in: input.authors };
    console.log("Authors filter:", matchStage["author.username"]);
    if (indexHint !== null && Object.keys(indexHint).length === 0)
      indexHint["author.username"] = 1;
  }

  pipeline.push({ $match: matchStage });
  console.log("Initial match stage:", JSON.stringify(matchStage, null, 2));

  // 2. Lookup stage to join with Product collection
  console.log("Adding lookup stage for Product collection");
  pipeline.push({
    $lookup: {
      from: "Product",
      localField: "productId",
      foreignField: "_id",
      as: "product",
    },
  });

  pipeline.push({ $unwind: "$product" });
  console.log("Product lookup and unwind stages added");

  // 3. Match stage for product-related filters
  console.log("Building product-related match stage");
  const productMatchStage: any = {};

  if (input.brands.length > 0) {
    productMatchStage["product.brand"] = { $in: input.brands };
    console.log("Brands filter:", productMatchStage["product.brand"]);
  }

  if (input.productNames.length > 0) {
    productMatchStage["product.name"] = { $in: input.productNames };
    console.log("Product Names filter:", productMatchStage["product.name"]);
  }

  if (Object.keys(productMatchStage).length > 0) {
    pipeline.push({ $match: productMatchStage });
    console.log(
      "Product match stage added:",
      JSON.stringify(productMatchStage, null, 2)
    );
  } else {
    console.log("No product-specific filters applied");
  }

  // 4. Sorting (최적화를 위해 앞으로 이동)
  console.log("Adding sort stage");
  const sortStage = getSortStage(input.sortBy);
  pipeline.push({ $sort: sortStage });
  console.log("Sort stage:", sortStage);

  // 5. Pagination (skip과 limit을 앞으로 이동)
  const skip = (input.page - 1) * input.limit;
  pipeline.push({ $skip: skip });
  pipeline.push({ $limit: input.limit });

  // 6. Project stage
  console.log("Adding project stage");
  pipeline.push({
    $project: {
      productName: "$product.name",
      userName: "$author.username",
      rating: 1,
      createdAt: 1,
      likeCount: 1,
      platform: 1,
      userImage: "$author.avatar",
      productAverageRating: "$product.averageRating",
      productReviewCount: "$product.reviewCount",
      content: 1,
    },
  });

  console.log("Final pipeline:", JSON.stringify(pipeline, null, 2));
  console.log("Index hint:", indexHint);

  // 7. Count total documents (별도의 쿼리로 수행)
  const countPipeline = [
    { $match: matchStage },
    {
      $lookup: {
        from: "Product",
        localField: "productId",
        foreignField: "_id",
        as: "product",
      },
    },
    { $unwind: "$product" },
    ...(Object.keys(productMatchStage).length > 0
      ? [{ $match: productMatchStage }]
      : []),
    { $count: "total" },
  ];

  try {
    console.log("Executing aggregation pipeline");
    let reviewsQuery = Review.aggregate(pipeline);
    let countQuery = Review.aggregate(countPipeline);

    // 인덱스 힌트가 null이 아닐 때만 힌트 적용
    if (indexHint !== null) {
      reviewsQuery = reviewsQuery.hint(indexHint);
      countQuery = countQuery.hint(indexHint);
    }

    const [reviews, countResult] = await Promise.all([
      reviewsQuery,
      countQuery,
    ]);

    const totalCount = countResult.length > 0 ? countResult[0].total : 0;

    console.log("Query results:", { totalCount, reviewsCount: reviews.length });

    return res.status(200).json({
      reviews,
      totalCount,
      currentPage: input.page,
      totalPages: Math.ceil(totalCount / input.limit),
    });
  } catch (error) {
    console.error("Error querying reviews:", error);
    throw error;
  }
};
