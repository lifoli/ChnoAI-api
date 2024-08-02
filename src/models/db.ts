import { createClient } from "@supabase/supabase-js";

import dotenv from "dotenv";

dotenv.config();

const supabaseUrl: string = "https://oocwfpitekaomlpwbtxh.supabase.co";
const supabaseKey: string =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vY3dmcGl0ZWthb21scHdidHhoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjIzOTY4OTQsImV4cCI6MjAzNzk3Mjg5NH0.ScApn2A0_RMiTl8aFXfB7IGpRZvUEAwlnx8FmqTbzv0";
const supabase = createClient(supabaseUrl, supabaseKey);

export default supabase;
