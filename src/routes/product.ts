import express from "express";

const product = require("../controllers/productController");

const router = express.Router();

router.post("/info", product.getProductByName);

module.exports = router;
