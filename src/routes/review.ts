import express from "express";
import Product from "../models/Product";

// import review from "../controllers/reviewController";

const review = require("../controllers/reviewController");
const product = require("../controllers/productController");
const router = express.Router();

//고객별 리뷰검색 페이지 api
router.get("/test", review.test);

router.get("/userinfo/:username", review.getReviewSummaryByUsername);

router.get("/user/:username", review.getReviewsByUsername);

router.get("/useractivitytrend/:username", review.getUserActivityTrend);

router.get("/product/wordcloud/:productname", product.generateWordCloudData);

router.post("/product/trend", review.getProductActivityTrend);

// 리뷰 검색 API 엔드포인트
router.post("/search", review.searchReviews);

module.exports = router;
