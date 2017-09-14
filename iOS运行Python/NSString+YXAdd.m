//
//  NSString+YXAdd.m
//  iOS运行Python
//
//  Created by  谭德林 on 2017/9/11.
//  Copyright © 2017年 yj. All rights reserved.
//

#import "NSString+YXAdd.h"

@implementation NSString (YXAdd)
+(const char *)yx_stringToChar:(NSString *)string
{
    return [string UTF8String];
}

+(NSString *)yx_charToString:(const char *)cString
{
    return [NSString stringWithUTF8String:cString];
}
@end
