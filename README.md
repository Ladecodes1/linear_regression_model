# Maize Yield Prediction for Smallholder Farmers

## Mission and problem
My mission is to help smallholder farmers, especially young farmers, grow more food with less guesswork.
Problem: maize yields vary widely between farms, and farmers rarely know which practices matter most.
This project predicts maize yield (kg per hectare) from farm conditions and practices, so farmers and extension officers can plan better.

## Dataset
The data is a real survey of smallholder maize fields collected by One Acre Fund in Sub-Saharan Africa (Kenya, Tanzania, Rwanda, Burundi, Zambia, Uganda and Nigeria) between 2016 and 2022. It has 14,773 fields and 53 columns covering weather, soil, planting, seed type, fertiliser and pests, with the measured maize yield as the target.

Source: "Maize management and yield of smallholder farmers in Sub-Saharan Africa between 2016 and 2022" (One Acre Fund), Zenodo: https://zenodo.org/doi/10.5281/zenodo.11115815

License: Creative Commons Attribution 4.0 International (CC BY 4.0). Credit: One Acre Fund.

## Swagger UI (public API link)
https://maize-yield-api-93ln.onrender.com/docs

## Demo video
https://youtu.be/oYRqLTaedTo

## Mobile app (Flutter)

Requirements: Flutter SDK, and an Android emulator or phone.

1. Clone the repo and go to the app folder:
   ```
   git clone https://github.com/Ladecodes1/linear_regression_model.git
   cd linear_regression_model/summative/FlutterApp
   ```
2. Install packages:
   ```
   flutter pub get
   ```
3. Start an Android emulator or plug in a phone, then check it appears:
   ```
   flutter devices
   ```
4. Run the app:
   ```
   flutter run -d <device-id>
   ```

The app calls the public API at https://maize-yield-api-93ln.onrender.com/predict.
The first request can take up to a minute while the free server wakes up.

Example input to test the app:

| Field | Example |
|---|---|
| Country | rwanda |
| Elevation (metres) | 1636 |
| Plants per square metre | 3.5 |
| Hybrid seed (1 = yes, 0 = no) | 0 |
| Nitrogen (kg per hectare) | 0 |
| Phosphorus (kg per hectare) | 0 |
| Season rainfall (mm) | 620.8 |
