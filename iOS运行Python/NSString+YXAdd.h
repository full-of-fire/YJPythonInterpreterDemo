//
//  NSString+YXAdd.h
//  iOS运行Python
//
//  Created by  谭德林 on 2017/9/11.
//  Copyright © 2017年 yj. All rights reserved.
//

#import <Foundation/Foundation.h>

@interface NSString (YXAdd)
+(const char *)yx_stringToChar:(NSString *)string;
+(NSString *)yx_charToString:(const char *)cString;
@end
